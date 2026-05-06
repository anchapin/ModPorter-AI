# Monitoring and Alerting Guide

This document describes the monitoring stack and alerting configuration for the PortKit conversion pipeline.

**Issue**: #1150 - Pre-beta: Production error monitoring and pipeline alerting

## Overview

PortKit uses a multi-layer monitoring approach:

| Layer | Tool | Purpose |
|-------|------|---------|
| Error Tracking | Sentry | Real-time error monitoring, pipeline alerting |
| Metrics | Prometheus | Conversion rates, performance metrics |
| Logs | Better Stack | Centralized log aggregation |
| Alerting | Sentry Alerts + Slack | Notifications when thresholds exceeded |

## Sentry Configuration

### Environment Variables

```bash
# Required
SENTRY_DSN=https://your-dsn@sentry.io/project

# Optional (defaults shown)
SENTRY_ENVIRONMENT=production  # or staging, development
SENTRY_TRACES_SAMPLE_RATE=0.1   # 10% of transactions traced
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% of profiles collected
SENTRY_ENABLE_DEV=false          # Set true to enable in development
```

### FastAPI Integration

Sentry is initialized in `backend/src/main.py` during startup:

```python
from services.sentry_config import init_sentry

@app.on_event("startup")
async def startup_event():
    init_sentry()
```

### Celery Worker Integration

Sentry is initialized in `backend/src/services/celery_tasks.py`:

```python
from services.sentry_config import init_celery_sentry

# Initialize before any tasks run
init_celery_sentry()
```

## Alerting Rules

### 1. Conversion Failure Rate Alert

**Trigger**: Conversion failure rate exceeds 5% in a 5-minute window

**Configuration** (Sentry Dashboard):
```
Alert Name: Conversion Failure Rate High
Condition: portkit_conversion_failure_rate_percent > 5
Time Window: 5 minutes
Severity: warning

Actions:
  - Slack: #beta-alerts (warning channel)
  - Email: ops@portkit.com
```

### 2. Pipeline Error Spike

**Trigger**: More than 10 conversion errors in 1 minute

**Configuration** (Sentry Dashboard):
```
Alert Name: Pipeline Error Spike
Condition: count(errors where tags.pipeline = "conversion") > 10
Time Window: 1 minute
Severity: critical

Actions:
  - Slack: #beta-alerts (urgent channel)
  - PagerDuty: Engineering on-call
```

### 3. Celery Task Failure

**Trigger**: Any Celery task fails after all retries exhausted

**Configuration** (Sentry Dashboard):
```
Alert Name: Celery Task Failed
Condition: count(tasks where status = "failed" and task.name starts with "services.celery_tasks") > 0
Time Window: 5 minutes
Severity: error

Actions:
  - Slack: #beta-alerts
```

### 4. LLM Inference Errors

**Trigger**: More than 5 LLM errors in 5 minutes

**Configuration**:
```
Alert Name: LLM Inference Error Spike
Condition: count(errors where tags.pipeline = "llm_inference") > 5
Time Window: 5 minutes
Severity: warning

Actions:
  - Slack: #ai-engine-alerts
```

## Prometheus Metrics

The following metrics are exposed at `/metrics` for Prometheus scraping:

### Conversion Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `portkit_conversion_jobs_total` | Counter | Total conversion jobs by status |
| `portkit_conversion_duration_seconds` | Histogram | Conversion duration distribution |
| `portkit_conversion_success_rate` | Gauge | Current success rate percentage |
| `portkit_conversion_failure_rate_percent` | Gauge | Current failure rate percentage |
| `portkit_conversions_completed_total` | Gauge | Total successful conversions |
| `portkit_conversions_failed_total` | Gauge | Total failed conversions |

### Error Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `portkit_errors_total` | Counter | Errors by category, type, source |
| `portkit_error_rate_per_minute` | Gauge | Current error rate |
| `portkit_retry_attempts_total` | Counter | Retry attempts |

### Queue Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `portkit_conversion_queue_size` | Gauge | Jobs in queue |
| `portkit_active_conversions` | Gauge | Currently processing jobs |
| `celery_task_latency_seconds` | Histogram | Task processing latency |

## Grafana Dashboard

Import the dashboard JSON from `docs/grafana-dashboard.json` for:

- **Conversion Pipeline Overview**: Success/failure rates, queue depth
- **Agent Performance**: Per-agent execution times and success rates
- **LLM Usage**: Token consumption, cost tracking
- **System Health**: Database, Redis, API latency

## Log Aggregation (Better Stack)

Logs are shipped to Better Stack for centralized viewing:

```python
from services.log_aggregation import get_better_stack_handler

handler = get_better_stack_handler()
if handler:
    logging.root.addHandler(handler)
```

### Log Levels

| Level | Use Case |
|-------|----------|
| DEBUG | Detailed debugging info (development only) |
| INFO | Normal operation events |
| WARNING | Recoverable issues, retries |
| ERROR | Failures that need attention |
| CRITICAL | System failures |

## Health Check Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic liveness check |
| `GET /health/liveness` | Kubernetes liveness probe |
| `GET /health/readiness` | Kubernetes readiness probe (checks DB + Redis) |

See `docs/health-checks.md` for full details.

## Alert Response Runbook

### High Conversion Failure Rate

1. Check Sentry for error patterns: `tags.pipeline = "conversion" AND error.type = "*"`
2. Identify failing stage: parsing, translation, packaging
3. Check AI Engine health: `curl localhost:8001/health`
4. Review recent deployments
5. If AI Engine issue: escalate to AI team

### Celery Worker Issues

1. Check worker logs: `docker logs portkit-celery-worker`
2. Verify Redis connectivity
3. Check for dead letter queue buildup: `redis-cli zcard portkit:dead_letter`
4. Restart workers if needed: `docker-compose restart celery-worker`

### Database Connection Issues

1. Check pg Pod status: `kubectl get pods -n portkit`
2. View connection pool metrics
3. Check for long-running queries
4. Consider scaling connection pool

## Related Issues

- Issue #1150: Production error monitoring and pipeline alerting (this implementation)
- Issue #1212: Full observability stack (Better Stack integration)
- Issue #384: Monitoring dashboards with Grafana/Prometheus