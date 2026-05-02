# Portkit Observability Runbook

## Overview

This runbook documents the observability stack for Portkit, including log aggregation, Celery queue monitoring, distributed tracing, and on-call alerting.

**Issue**: [#1212](https://github.com/anchapin/portkit/issues/1212) - Pre-beta: Full observability stack

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Portkit Stack                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐   │
│  │   FastAPI   │────▶│    Redis    │────▶│  Celery Workers     │   │
│  │   Backend  │     │             │     │                     │   │
│  └──────┬──────┘     └─────────────┘     └─────────────────────┘   │
│         │                                            │               │
│         ▼                                            ▼               │
│  ┌─────────────┐                              ┌─────────────────┐   │
│  │   Better    │                              │  celery-exporter │   │
│  │   Stack    │                              │   (:9540)       │   │
│  │  Logtail   │                              └────────┬────────┘   │
│  └─────────────┘                                       │               │
│                                                        ▼               │
│                                               ┌─────────────────┐   │
│  ┌─────────────┐                              │   Prometheus    │   │
│  │   Open     │───────────────────────────────▶│                 │   │
│  │ Telemetry  │                              └────────┬────────┘   │
│  │ (OTLP)     │                                       │               │
│  └─────────────┘                                       ▼               │
│                                                ┌─────────────────┐   │
│  ┌─────────────┐                              │    Grafana      │   │
│  │  Better     │                              │                 │   │
│  │  Stack      │                              └─────────────────┘   │
│  │  Incidents  │                                                      │
│  └─────────────┘                                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. Log Aggregation (Better Stack Logtail)

### Purpose
- Searchable, persistent log storage with 30-day retention
- Alertable logs (not just real-time tail like `flyctl logs`)
- Structured logging with trace correlation

### Configuration

**Environment Variables**:
```bash
BETTERSTACK_SOURCE_TOKEN=<your-source-token>
BETTERSTACK_API_TOKEN=<your-api-token>
```

### Quick Start

1. Create a Better Stack account at https://betterstack.com
2. Create a new source of type "Cloudflare Logpush" or "HTTP"
3. Copy the source token
4. Set `BETTERSTACK_SOURCE_TOKEN` in Fly.io secrets

### Fly.io Log Shipping

For Fly.io, logs are typically shipped via the Better Stack logshipper or directly via the `BetterStackHandler` in `backend/src/services/log_aggregation.py`.

Reference: https://betterstack.com/docs/logs/fly-io/

### Using the Structured Logger

```python
from backend.src.services.log_aggregation import StructuredLogger

logger = StructuredLogger("portkit")

# Set trace context for correlation
logger.set_trace_context(trace_id="abc123", span_id="def456")

# Log with context
logger.info("Processing conversion", context={"job_id": "job123", "file_id": "file456"})

# Log with additional context
logger.set_context(user_id="user123")
logger.info("User action triggered")  # Includes user_id in context
```

### Log Query Examples

```sql
-- Find all errors for a specific trace
SELECT * FROM logs WHERE trace_id = 'abc123' AND level = 'ERROR'

-- Find all conversions with duration > 60s
SELECT * FROM logs WHERE message LIKE '%conversion%' AND context->>'duration' > 60

-- Error rate by minute
SELECT date_trunc('minute', timestamp) as minute, count(*)
FROM logs WHERE level = 'ERROR'
GROUP BY minute ORDER BY minute DESC
```

---

## 2. Celery Queue Monitoring

### Purpose
- Queue depth visibility
- Task failure rate monitoring
- Worker utilization tracking
- Stuck job detection

### Components

1. **celery-exporter** - Exports Celery metrics in Prometheus format
2. **CeleryQueueMonitor** - Python client for queue metrics
3. **Prometheus** - Scrapes and stores metrics
4. **Grafana** - Dashboards and alerting

### Metrics Available

| Metric | Type | Description |
|--------|------|-------------|
| `celery_queue_depth` | Gauge | Total tasks in all queues |
| `celery_queue_size` | Gauge | Tasks per queue (with `queue` label) |
| `celery_workers_online` | Gauge | Number of online workers |
| `celery_tasks_total` | Counter | Total tasks by state |
| `celery_task_runtime_seconds` | Histogram | Task duration |
| `celery_dead_letter_queue_size` | Gauge | Failed tasks in DLQ |

### CeleryQueueMonitor Usage

```python
from backend.src.services.celery_monitoring import get_celery_monitor

monitor = get_celery_monitor()

# Get queue stats
stats = monitor.get_queue_stats()

# Check queue health
health = monitor.check_queue_health()
if not health["healthy"]:
    for issue in health["issues"]:
        print(f"Issue: {issue}")

# Get Prometheus-format metrics
metrics = monitor.get_queue_depth_prometheus()
```

### Grafana Dashboard

Import dashboard ID **10026** from Grafana.com (Celery Monitoring).

Reference: https://grafana.com/grafana/dashboards/10026

### Alert Rules

See `monitoring/alert_rules.yml` for configured alert rules:

| Alert | Severity | Condition |
|-------|----------|-----------|
| `CeleryQueueDepthHigh` | P1 | Queue > 100 for 5m |
| `CeleryTaskFailureRateHigh` | P1 | Failure rate > 10% over 5m |
| `CeleryWorkersOffline` | P0 | Workers == 0 for 1m |
| `CeleryTaskDurationP95High` | P2 | P95 duration > 120s |
| `CeleryDeadLetterQueueHigh` | P2 | DLQ > 50 for 5m |

---

## 3. Distributed Tracing (OpenTelemetry)

### Purpose
- Trace requests across API → Redis → Celery → converter
- Identify which step causes slow conversions
- Correlate logs with traces

### Configuration

**Environment Variables**:
```bash
TRACING_EXPORTER=betterstack
BETTERSTACK_OTLP_ENDPOINT=https://otlp.betterstack.com/v1/traces
BETTERSTACK_API_TOKEN=<your-api-token>
```

### Instrumented Components

- **FastAPI** - HTTP request/response tracing
- **HTTPX** - External API call tracing
- **Redis** - Cache operation tracing
- **Celery** - Task execution tracing

### Trace Context Propagation

```python
from backend.src.services.tracing import inject_trace_context, extract_trace_context

# Inject trace context into carrier (e.g., HTTP headers)
headers = {}
inject_trace_context(headers)

# Extract trace context from carrier
context = extract_trace_context(headers)
```

### Trace ID in Logs

The trace ID is automatically added to log context:

```python
from backend.src.services.tracing import get_trace_id

trace_id = get_trace_id()  # Get current trace ID
logger.info(f"Processing request", extra={"trace_id": trace_id})
```

---

## 4. On-Call Alerting (Better Stack Incidents)

### Purpose
- P0/P1 alerts reach a human at 3am
- Phone/SMS escalation for critical incidents
- On-call schedule management

### Alert Severity Levels

| Severity | Description | Escalation |
|----------|-------------|------------|
| P0 | All systems down, data loss | Immediate phone call |
| P1 | Major feature broken | SMS + push in 5min |
| P2 | Degraded performance | Push notification |
| P3 | Minor issue | Email next business day |

### Alert Manager Usage

```python
from backend.src.services.alerting import get_alert_manager, AlertSeverity

manager = get_alert_manager()

# Trigger an alert
await manager.trigger_alert(
    name="queue_backlog_critical",
    message="Queue backlog exceeded 1000 tasks",
    severity=AlertSeverity.P0_CRITICAL,
    metadata={"queue_depth": 1500}
)

# Resolve an alert
await manager.resolve_alert("queue_backlog_critical")
```

### On-Call Schedule Setup

1. Go to Better Stack → Incidents → On-Call Schedules
2. Create a schedule for Alex
3. Add escalation policy:
   - P0: Phone call immediately
   - P1: SMS in 5 minutes, phone in 15 minutes
   - P2: Push notification
   - P3: Email next business day

### LLM Cost Alert Integration

Alert for cost spikes (#1205) should route through the same on-call system:

```python
# When LLM cost exceeds threshold
await manager.trigger_alert(
    name="llm_cost_spike",
    message=f"LLM cost rate: ${cost_rate}/hour",
    severity=AlertSeverity.P1_HIGH,
    metadata={"cost_rate": cost_rate, "budget": budget}
)
```

---

## 5. Quick Reference

### Environment Variables

```bash
# Better Stack
BETTERSTACK_SOURCE_TOKEN=    # Log source token
BETTERSTACK_API_TOKEN=        # API token for incidents

# Tracing
TRACING_EXPORTER=betterstack  # jaeger, otlp, betterstack, all
BETTERSTACK_OTLP_ENDPOINT=    # Better Stack OTLP endpoint

# Celery
REDIS_URL=redis://localhost:6379/0
CELERY_NAMESPACE=portkit
```

### Service Endpoints

| Service | URL | Purpose |
|---------|-----|---------|
| Prometheus | http://localhost:9090 | Metrics storage |
| Grafana | http://localhost:3001 | Dashboards |
| celery-exporter | http://localhost:9540/metrics | Celery metrics |
| Better Stack | https://betterstack.com | Logs & Incidents |

### Common Queries

```sql
-- Find conversion errors in last hour
SELECT * FROM logs
WHERE level = 'ERROR'
  AND message LIKE '%conversion%'
  AND timestamp > NOW() - INTERVAL '1 hour'

-- Queue depth over time
SELECT date_trunc('minute', timestamp) as minute,
       avg(value) as avg_depth
FROM metrics
WHERE name = 'celery_queue_depth'
  AND timestamp > NOW() - INTERVAL '1 day'
GROUP BY minute ORDER BY minute DESC

-- Failed tasks by type
SELECT metric_labels->>'task_name' as task_name,
       sum(value) as failures
FROM metrics
WHERE name = 'celery_tasks_total'
  AND labels->>'state' = 'failure'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY task_name
```

---

## Troubleshooting

### Logs not appearing in Better Stack

1. Check `BETTERSTACK_SOURCE_TOKEN` is set correctly
2. Verify network access to `in.logs.betterstack.com`
3. Check if structured logger is properly configured

### Celery metrics not showing

1. Verify celery-exporter is running: `curl localhost:9540/metrics`
2. Check Redis connectivity: `redis-cli ping`
3. Verify Prometheus is scraping celery-exporter

### Alerts not firing

1. Check Prometheus targets: http://localhost:9090/targets
2. Verify alert rules loaded: http://localhost:9090/rules
3. Check alert history in Better Stack

### Tracing not working

1. Set `TRACING_CONSOLE=true` to enable console exporter for debugging
2. Check `BETTERSTACK_OTLP_ENDPOINT` is accessible
3. Verify OpenTelemetry packages installed

---

## Dependencies

- **#1150** - Sentry error tracking (complementary)
- **#1153** - Status page (Better Stack includes status page)
- **#1205** - LLM cost monitoring (uses same alerting)
- **#1211** - Incident response runbook (this document)
