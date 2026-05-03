# Scalability Assessment: API & Frontend Scale-Up/Scale-Down

**Issue**: #1202  
**Status**: Architecture Assessment  
**Last Updated**: 2026-05-02

---

## Executive Summary

This document provides a comprehensive scalability assessment for the portkit API and frontend infrastructure. The current stack has solid foundations but contains several **blocking issues** that must be resolved before horizontal scaling can function correctly in multi-instance deployments.

**Verdict**: Horizontal scaling is **not safe to enable today** due to in-memory job state and local volume storage. Addressing these two P0 items is the prerequisite for all other scaling work.

---

## Current Architecture

| Layer | Technology | Deployment | Scalability Status |
|-------|-----------|------------|-------------------|
| Frontend | React 19 + Vite, nginx | Docker container, port 3000 | Single instance |
| Backend API | FastAPI (async) + asyncpg | Fly.io `shared-cpu-1x`, 1024MB | No auto-scale config |
| AI Engine | FastAPI + WorkerPool | Same Fly.io VM via docker-compose | Co-located with backend |
| Background Jobs | Celery + Redis | Same VM, fixed `--concurrency=4` | Hardcoded concurrency |
| Database | PostgreSQL (async SQLAlchemy) | Fly.io managed Postgres | Single instance, no replicas |
| Cache / Broker | Redis | Docker service | Connection pooled |
| File Storage | Local Docker volumes | `conversion-cache`, `temp-uploads`, `conversion-outputs` | Not shared across instances |
| Tracing | Jaeger | Sidecar | Present |
| AV Scanning | ClamAV | Sidecar | Tax on every instance |

---

## Critical Blockers (Must Fix Before Horizontal Scaling)

### P0 - In-Memory Job State Breaks Multi-Instance Deploys

**Location**: `backend/src/main.py:101`

```python
conversion_jobs_db: Dict[str, "ConversionJob"] = {}
```

**Problem**: The `conversion_jobs_db` dictionary holds all job state in process memory. With two or more backend instances behind Fly.io's load balancer:
- Job submitted to instance A -> stored in A's memory
- Status poll lands on instance B -> 404 (B has no knowledge of the job)

**Evidence**: Multiple write/read operations on `conversion_jobs_db[job_id]` throughout `main.py` (lines 498, 529, 571, 765, 793, 930, 947, 1015, 1130, 1179, 1226). The download endpoint at `main.py:1247` uses this dict directly.

**Impact**: Any multi-instance deployment returns inconsistent results. Users experience random 404s on job status and downloads.

**Fix**: Migrate job state fully to Redis + Postgres. Remove `conversion_jobs_db` dictionary entirely. The `download_converted_mod` endpoint must query Redis/DB, not an in-memory dict.

---

### P0 - Local Volumes Prevent Shared File Access Across Instances

**Locations**:
- `docker-compose.prod.yml:36` - `conversion-cache:/app/cache`
- `docker-compose.prod.yml:60-61` - `model-cache:/app/models`
- `main.py:96-97` - `TEMP_UPLOADS_DIR`, `CONVERSION_OUTPUTS_DIR` as local paths
- `docker-compose.prod.yml:238-241` - all volumes defined as `driver: local`

**Problem**: Conversion artifacts (`temp-uploads`, `conversion-outputs`, `conversion-cache`, `model-cache`) are mounted as local Docker volumes. A second backend or AI engine instance on a different machine **cannot read files written by the first instance**.

**Impact**: When scaling to multiple backend instances:
- Instance A uploads a file to `/app/data/temp_uploads/{file_id}.jar`
- AI engine on Instance B cannot find the file -> conversion fails
- Results written to Instance A's volume are not accessible from Instance B

**Fix**: Replace local volumes with object storage. Fly.io has native [Tigris](https://fly.io/docs/tigris/) (S3-compatible). The `core/storage.py` module already has a `StorageManager` abstraction with an S3 backend stub - implement it.

---

## High Priority Issues (Limits Effective Scaling)

### AI Engine Colocated With Backend on Single VM

**Current**: `docker-compose.prod.yml:47-76` runs AI engine in the same VM as backend.

**Problem**: The AI engine is the most CPU/memory-intensive component (LLM inference, file parsing, WorkerPool). Under load, it competes with the backend for the same `shared-cpu-1x` CPU budget and 1024MB memory ceiling.

**Fix**: Extract AI Engine to its own Fly.io app (`portkit-ai-engine`). This allows:
- Independent vertical sizing: `performance-cpu-2x` for AI, `shared-cpu-1x` for API
- Independent horizontal scaling based on queue depth
- Separate teams/deployments for AI vs API

---

### No Fly.io Auto-Scale Configuration

**Current `fly.toml`**:
```toml
[[services]]
  auto_start_machines = true
  min_machines_running = 1
  # No concurrency limits, no max count
```

**Problem**: Fly.io cannot auto-scale without concurrency or soft/hard limits configured.

**Fix**: Add `[[services.concurrency]]` block and `max_machines_running`:
```toml
[[services.concurrency]]
  type = "requests"
  soft_limit = 50
  hard_limit = 100

[http_service]
  min_machines_running = 1
  max_machines_running = 5
  auto_stop_machines = true
  auto_start_machines = true
```

---

### Celery Worker Concurrency Hardcoded

**Current `fly.toml:20`**:
```toml
worker = "sh -c '... celery ... --concurrency=4'"
```

**Fix**: Use `--autoscale=8,2` (max 8, min 2):
```toml
worker = "sh -c '... celery ... --autoscale=8,2'"
```

---

## Lower Priority - Optimizations

### Frontend Should Be CDN-Delivered

**Current**: React SPA runs as a Docker nginx container.

**Problem**: The React SPA builds to static files. Running it in Docker consumes compute for serving files that could be served from a CDN at near-zero cost with infinite scale.

**Fix**: Deploy frontend to Vercel, Cloudflare Pages, or Fly.io static asset hosting.

---

### No Database Read Replicas

**Current**: All queries hit the same Postgres primary.

**Fix**: Add Fly.io Postgres read replica. Route `SELECT`-only endpoints to a `readonly_database_url` setting.

---

### ClamAV as Sidecar Is a Scaling Tax

**Problem**: ClamAV takes ~120s to start and consumes ~200MB RAM on every backend machine.

**Fix**: Share one ClamAV instance across multiple backend replicas via Fly.io private network.

---

## Recommended Target Architecture

```
                     +---------------------+
                     |  Cloudflare / CDN   |  <- Frontend (static)
                     +----------+---------+
                                |
                     +----------v---------+
                     |  Fly.io LB / Proxy   |
                     +----------+---------+
                                |
            +-------------------+-------------------+
            |                   |                   |
   +--------v-------+  +--------v--------+  +------v-------+
   |  Backend API  |  |  Backend API     |  |  Backend API  |  <- Fly.io auto-scale 1-5
   |  (shared-1x)   |  |  (shared-1x)      |  |  (shared-1x)   |
   +-------+--------+  +--------+---------+  +------+-------+
            +---------------------+---------------------+
                               |
                     +---------v----------+
                     |    Redis (broker)  |  <- Job state + rate limits
                     +------+-----+-----+
                            |     |
              +-------------v-+  +-v-------------+
              | Celery Worker  |  |  AI Engine   |  <- Separate Fly.io app
              |  (autoscale)   |  |  (perf-cpu-2x)|
              +----------------+  +------+-------+
                                          |
                     +--------------------v-------------------+
                     |  Tigris / S3 Object Storage             |  <- Shared across all instances
                     +------------------------------------------+
                     +------------------------------------------+
                     |  Postgres (+ read replica)                |
                     +------------------------------------------+
```

---

## Implementation Order

| Priority | Task | Effort | Blocks Horizontal Scaling |
|----------|------|--------|---------------------------|
| P0 | Migrate in-memory `conversion_jobs_db` to Redis/Postgres | S | Yes |
| P0 | Replace local volumes with Tigris/S3 | M | Yes |
| P1 | Add Fly.io auto-scale config to fly.toml | XS | Elastic scale |
| P1 | Extract AI Engine to separate Fly.io app | M | Independent AI scaling |
| P1 | Celery autoscale config (`--autoscale=8,2`) | XS | Worker elasticity |
| P2 | Deploy frontend to CDN | S | Frontend scale |
| P2 | Postgres read replica + read-only routing | M | DB at scale |
| P3 | ClamAV shared service | M | Resource efficiency |

---

## What's Already Working Well

| Component | Status | Notes |
|-----------|--------|-------|
| Async FastAPI + asyncpg | Working | Non-blocking I/O throughout |
| Redis + Celery | Working | Correct pattern for long-running conversions |
| WorkerPool in AI engine | Working | Thread/process pools |
| Rate limiting middleware | Working | Redis-backed sliding window |
| k6 load tests | Working | Smoke, load, stress, spike scenarios |
| Health checks | Working | On all services |
| Jaeger distributed tracing | Working | Present |
| Separate staging + prod Fly.io apps | Working | Configured |
| `auto_start_machines = true` | Working | Already enabled |

---

## Metrics to Monitor for Scaling Decisions

### Infrastructure
- **CPU utilization**: Target <70% sustained -> scale up
- **Memory utilization**: Target <80% sustained -> scale up
- **Disk I/O**: Target <70% -> investigate storage bottleneck
- **Network throughput**: Monitor for saturation

### Application
- **Request rate** (req/s): Baseline and peak
- **Response time** (p50, p95, p99): p95 >2s indicates need to scale
- **Error rate**: Target <0.1%; >1% warrants investigation
- **Queue depth**: >50 pending -> scale Celery workers
- **WebSocket connections**: Monitor for sticky session issues

### Business
- **Conversions/hour**: Capacity planning
- **Cost/conversion**: Optimize for efficiency
- **Active users**: Correlate with infrastructure spend

---

## Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU | >70% | >90% | Scale up API instances |
| Memory | >80% | >95% | Scale up or optimize |
| Error Rate | >1% | >5% | Investigate |
| Response Time p95 | >1s | >3s | Profile hot paths |
| Queue Depth | >50 | >200 | Scale Celery workers |
| Job processing time | >300s | >600s | Investigate AI engine bottleneck |

---

## Appendix: Related Documentation

- `docs/INFRASTRUCTURE-SCALING.md` - Historical scaling plan with cost projections
- `docs/ARCHITECTURE.md` - System architecture overview
- `docs/adr/0003-use-redis-for-caching-and-rate-limiting.md` - Redis usage decisions