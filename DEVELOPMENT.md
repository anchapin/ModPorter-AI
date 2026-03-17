# ModPorter-AI Development Setup Guide

**Version**: 1.0  
**Last Updated**: 2026-03-13

---

## Quick Start

Get up and running in 5 minutes:

```bash
# 1. Clone the repository
git clone https://github.com/your-org/modporter-ai.git
cd modporter-ai

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
docker-compose up -d

# 4. Check service health
docker-compose ps

# 5. Run database migrations
docker-compose exec backend alembic upgrade head
```

---

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | React application |
| **Backend API** | http://localhost:8080 | FastAPI backend |
| **API Docs** | http://localhost:8080/docs | Swagger UI (ReDoc) |
| **Grafana** | http://localhost:3001 | Metrics dashboards (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **Jaeger** | http://localhost:16686 | Distributed tracing |
| **Redis Commander** | http://localhost:8085 | Redis web UI |

---

## Prerequisites

- **Docker Desktop** (v20.10+) or Docker Engine + Docker Compose
- **Git** (v2.30+)
- **Optional**: VS Code with Docker extension
- **Optional**: Python 3.11+ for local backend development
- **Optional**: Node.js 18+ and pnpm for local frontend development

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Development Environment                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Frontend │───▶│ Backend  │───▶│AI Engine │              │
│  │  :3000   │    │  :8080   │    │  :8001   │              │
│  └──────────┘    └────┬─────┘    └────┬─────┘              │
│                       │               │                     │
│                       ▼               ▼                     │
│                ┌──────────┐    ┌──────────┐                │
│                │ Postgres │    │  Redis   │                │
│                │  :5433   │    │  :6379   │                │
│                └──────────┘    └──────────┘                │
│                       │               │                     │
│                       ▼               ▼                     │
│                ┌──────────┐    ┌──────────┐                │
│                │Prometheus│    │  Jaeger  │                │
│                │  :9090   │    │ :16686   │                │
│                └────┬─────┘    └──────────┘                │
│                     │                                       │
│                     ▼                                       │
│                ┌──────────┐                                │
│                │ Grafana  │                                │
│                │  :3001   │                                │
│                └──────────┘                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Docker Compose Services

### Core Services

**frontend** (React + Vite + Nginx)
- Port: 3000
- Hot reload enabled in development
- Depends on: backend

**backend** (FastAPI + Python 3.11)
- Port: 8080
- API docs: http://localhost:8080/docs
- Hot reload enabled in development
- Depends on: postgres, redis, jaeger

**ai-engine** (CrewAI + LangChain)
- Port: 8001
- Multi-agent AI conversion pipeline
- Depends on: redis, jaeger

### Infrastructure Services

**postgres** (PostgreSQL 15 + pgvector)
- Port: 5433 (external), 5432 (internal)
- Database: modporter
- User: postgres / password: password
- Extension: pgvector for RAG embeddings

**redis** (Redis 7)
- Port: 6379
- Job queue, caching, sessions
- Max memory: 256mb with LRU eviction

**jaeger** (Jaeger 1.58)
- Port: 16686 (UI), 14268 (collector)
- Distributed tracing via OTLP
- Storage: badger (embedded)

### Monitoring Services

**prometheus** (Prometheus 2.55)
- Port: 9090
- Scrapes metrics every 15s
- Retention: 7 days

**grafana** (Grafana 11.4)
- Port: 3001
- Login: admin / admin
- Pre-configured Prometheus datasource

**redis-commander** (Redis Web UI)
- Port: 8085
- Browse Redis keys and values
- No authentication (dev only)

---

## Common Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a service
docker-compose restart backend

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f ai-engine

# View specific service logs
docker-compose logs --tail=100 backend

# Rebuild a service
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Database Operations

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Rollback migrations
docker-compose exec backend alembic downgrade -1

# Check database connection
docker-compose exec postgres psql -U postgres -d modporter -c "SELECT 1;"

# Access PostgreSQL shell
docker-compose exec postgres psql -U postgres -d modporter

# List tables
docker-compose exec postgres psql -U postgres -d modporter -c "\dt"

# Check pgvector extension
docker-compose exec postgres psql -U postgres -d modporter -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Redis Operations

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Test Redis connection
docker-compose exec redis redis-cli ping

# View Redis keys
docker-compose exec redis redis-cli KEYS '*'

# Clear all Redis data (dev only!)
docker-compose exec redis redis-cli FLUSHALL
```

### Testing & Debugging

```bash
# Run backend tests
docker-compose exec backend pytest

# Run frontend tests
docker-compose exec frontend pnpm test

# Run backend linting
docker-compose exec backend ruff check src/

# Run frontend linting
docker-compose exec frontend pnpm lint

# Check service health
curl http://localhost:8080/api/v1/health
curl http://localhost:8001/api/v1/health
```

---

## Environment Variables

### Required Variables

Copy `.env.example` to `.env` and configure:

```bash
# API Keys (required for AI features)
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Database (defaults work for local dev)
DATABASE_URL=postgresql+asyncpg://postgres:password@postgres:5432/modporter
REDIS_URL=redis://redis:6379

# Application
LOG_LEVEL=INFO
DEBUG=true
```

### Optional Variables

```bash
# Rate limiting
RATE_LIMIT_PER_MINUTE=10
AI_RATE_LIMIT=5

# File upload limits
MAX_FILE_SIZE=104857600  # 100MB

# Feature flags
FEATURE_ANALYTICS=true
FEATURE_USER_ACCOUNTS=false
```

---

## Local Development

### Backend (Python)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run backend locally (without Docker)
export DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/modporter
export REDIS_URL=redis://localhost:6379
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Node.js)

```bash
# Install pnpm globally
npm install -g pnpm

# Install dependencies
cd frontend
pnpm install

# Run frontend locally
pnpm dev
```

---

## Monitoring & Observability

### Prometheus Metrics

Access metrics at: http://localhost:9090/metrics

**Key Metrics**:
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `conversion_jobs_total` - Total conversion jobs
- `conversion_jobs_success` - Successful conversions
- `conversion_jobs_failed` - Failed conversions

### Grafana Dashboards

Access Grafana at: http://localhost:3001 (admin/admin)

**Pre-configured Dashboards**:
- Backend API Performance
- Conversion Pipeline Metrics
- Redis Cache Performance
- PostgreSQL Query Performance
- Jaeger Tracing Overview

### Jaeger Tracing

Access Jaeger at: http://localhost:16686

**Trace Examples**:
- Full conversion pipeline trace
- API request traces
- Database query traces
- AI agent execution traces

---

## Common Issues & Solutions

### Issue: Port Already in Use

**Error**: `Bind for 0.0.0.0:3000 failed: port is already allocated`

**Solution**: Stop conflicting service or change port in docker-compose.yml:
```yaml
ports:
  - "3001:80"  # Change from 3000 to 3001
```

### Issue: Database Migration Fails

**Error**: `relation "users" does not exist`

**Solution**: Run migrations:
```bash
docker-compose exec backend alembic upgrade head
```

### Issue: pgvector Extension Not Found

**Error**: `could not open extension control file "vector"`

**Solution**: Ensure using correct PostgreSQL image:
```yaml
image: pgvector/pgvector:pg15  # Not just postgres:15
```

### Issue: Redis Connection Refused

**Error**: `Connection refused to redis:6379`

**Solution**: Check Redis health:
```bash
docker-compose ps redis
docker-compose logs redis
docker-compose exec redis redis-cli ping
```

### Issue: Frontend Can't Connect to Backend

**Error**: `Network request failed` or `ERR_CONNECTION_REFUSED`

**Solution**: Check API URL in frontend .env:
```bash
VITE_API_URL=http://localhost:8080/api/v1
```

### Issue: High Memory Usage

**Symptom**: Docker using >4GB RAM

**Solution**: Limit service memory in docker-compose.yml:
```yaml
services:
  ai-engine:
    deploy:
      resources:
        limits:
          memory: 2G
```

---

## Debugging Tips

### Backend Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Attach to running backend
docker-compose exec backend bash

# View structured logs
docker-compose logs backend | jq
```

### Frontend Debugging

```bash
# Open browser DevTools (F12)
# Check Console tab for errors
# Check Network tab for API calls
# React DevTools for component inspection
```

### Database Debugging

```bash
# Log all SQL queries
docker-compose exec postgres psql -U postgres -d modporter -c "ALTER SYSTEM SET log_statement = 'all';"
docker-compose restart postgres

# View slow queries
docker-compose exec postgres psql -U postgres -d modporter -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

### Performance Profiling

```bash
# Backend profiling
docker-compose exec backend python -m cProfile -o /tmp/profile.stats src/main.py

# Redis slow log
docker-compose exec redis redis-cli slowlog get 10
```

---

## Testing

### Run All Tests

```bash
# Backend tests
docker-compose exec backend pytest

# Frontend tests
docker-compose exec frontend pnpm test

# End-to-end tests
docker-compose exec frontend pnpm test:e2e
```

### Test Coverage

```bash
# Backend coverage
docker-compose exec backend pytest --cov=src --cov-report=html

# Frontend coverage
docker-compose exec frontend pnpm test:coverage
```

---

## Deployment

### Production Build

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.prod.yml up -d
```

### Backup & Restore

```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres modporter > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres modporter < backup.sql
```

---

## Next Steps

1. **Read API Documentation**: http://localhost:8080/docs
2. **Try Sample Conversion**: Upload a simple Java mod
3. **Check Monitoring**: Open Grafana at http://localhost:3001
4. **Join Community**: Discord server for support

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

---

## Support

- **Documentation**: https://docs.modporter.ai
- **Discord**: https://discord.gg/modporter-ai
- **GitHub Issues**: https://github.com/your-org/modporter-ai/issues
