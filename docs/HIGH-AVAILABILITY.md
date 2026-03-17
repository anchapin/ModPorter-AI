# High Availability Configuration

**ModPorter AI - Production HA Setup**

---

## Overview

High availability configuration for 99.9% uptime target.

---

## Architecture

```
                    ┌─────────────────┐
                    │   Cloudflare    │
                    │   (DNS + CDN)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Load Balancer  │
                    │   (HAProxy)     │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│   Frontend 1    │ │   Frontend 2    │ │   Frontend 3    │
│   (Nginx)       │ │   (Nginx)       │ │   (Nginx)       │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│   Backend 1     │ │   Backend 2     │ │   Backend 3     │
│   (FastAPI)     │ │   (FastAPI)     │ │   (FastAPI)     │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│   Primary DB    │ │   Replica 1     │ │   Replica 2     │
│   (PostgreSQL)  │ │   (Read-only)   │ │   (Read-only)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Load Balancer Configuration

### HAProxy Setup

**Installation:**
```bash
apt-get update
apt-get install -y haproxy
```

**Configuration** (`/etc/haproxy/haproxy.cfg`):
```haproxy
global
    log /dev/log local0
    log /dev/log local1 notice
    maxconn 4096
    daemon

defaults
    log global
    mode http
    option httplog
    option dontlognull
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    retries 3

frontend http_front
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/modporter.ai.pem
    http-request redirect scheme https unless { ssl_fc }
    
    # Health check endpoint
    acl is_health path_beg /api/v1/health
    use_backend health_backend if is_health
    
    # API routing
    acl is_api path_beg /api
    use_backend api_backend if is_api
    
    # Frontend routing
    default_backend frontend_backend

backend api_backend
    balance roundrobin
    option httpchk GET /api/v1/health
    http-check expect status 200
    
    server api1 backend1:8080 check inter 5s fall 3 rise 2
    server api2 backend2:8080 check inter 5s fall 3 rise 2
    server api3 backend3:8080 check inter 5s fall 3 rise 2

backend frontend_backend
    balance roundrobin
    option httpchk GET /
    http-check expect status 200
    
    server fe1 frontend1:80 check inter 5s fall 3 rise 2
    server fe2 frontend2:80 check inter 5s fall 3 rise 2
    server fe3 frontend3:80 check inter 5s fall 3 rise 2

backend health_backend
    server api1 backend1:8080 check inter 2s fall 2 rise 1
```

**Start HAProxy:**
```bash
systemctl enable haproxy
systemctl start haproxy
systemctl status haproxy
```

---

## Database High Availability

### PostgreSQL Streaming Replication

**Primary Configuration** (`postgresql.conf`):
```conf
wal_level = replica
max_wal_senders = 5
wal_keep_size = 1GB
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'
```

**Primary** (`pg_hba.conf`):
```conf
# Allow replication connections
host replication replicator 10.0.0.0/8 md5
```

**Replica Setup:**
```bash
# On replica server
pg_basebackup -h primary_host -U replicator -D /var/lib/postgresql/data -P -R
```

**Replica Configuration** (`postgresql.conf`):
```conf
hot_standby = on
primary_conninfo = 'host=primary_host port=5432 user=replicator password=secret'
```

### Read/Write Splitting

**Backend Configuration:**
```python
# Database routing
DATABASE_ROUTERS = {
    'write': 'postgresql://primary:5432/modporter',
    'read': [
        'postgresql://replica1:5432/modporter',
        'postgresql://replica2:5432/modporter',
    ]
}

# Use write for mutations, read for queries
async def get_db_write():
    async with AsyncSessionLocal(write=True) as session:
        yield session

async def get_db_read():
    async with AsyncSessionLocal(write=False) as session:
        yield session
```

---

## Redis High Availability

### Redis Sentinel Configuration

**Sentinel Config** (`sentinel.conf`):
```conf
sentinel monitor mymaster redis-primary 6379 2
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 60000
sentinel parallel-syncs mymaster 1

sentinel monitor myslave redis-replica1 6379 2
sentinel down-after-milliseconds myslave 5000
```

**Start Sentinel:**
```bash
redis-sentinel /etc/redis/sentinel.conf
```

**Client Configuration:**
```python
# Connect via Sentinel
from redis.sentinel import Sentinel

sentinel = Sentinel([('sentinel1', 26379), ('sentinel2', 26379)])
master = sentinel.master_for('mymaster')
slave = sentinel.slave_for('mymaster')

# Use master for writes, slave for reads
master.set('key', 'value')
value = slave.get('key')
```

---

## Auto-Scaling Configuration

### Docker Swarm Auto-Scaling

**Service Definition:**
```yaml
version: '3.8'

services:
  backend:
    image: modporter-ai-backend:latest
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

**Scale Service:**
```bash
docker service scale backend=5
```

### Kubernetes Auto-Scaling

**Horizontal Pod Autoscaler:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Apply HPA:**
```bash
kubectl apply -f hpa-backend.yaml
```

---

## Health Checks

### Endpoint Implementation

```python
# backend/src/api/health.py

@router.get("/health")
async def health_check():
    """Comprehensive health check."""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "ai_engine": await check_ai_engine(),
    }
    
    healthy = all(check["status"] == "healthy" for check in checks.values())
    
    return {
        "status": "healthy" if healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }

async def check_database():
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "latency_ms": latency}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Load Balancer Health Check

```haproxy
# HAProxy health check configuration
option httpchk GET /api/v1/health
http-check expect status 200
http-check expect string healthy
```

---

## Failover Procedures

### Database Failover

**Manual Failover:**
```bash
# Promote replica to primary
psql -h replica_host -U postgres -c "SELECT pg_promote();"

# Update application configuration
# Point to new primary
```

**Automatic Failover (Patroni):**
```yaml
# patroni.yml
scope: modporter
namespace: /db/
name: postgresql1

restapi:
  listen: 0.0.0.0:8008
  connect_address: postgresql1:8008

etcd:
  hosts: etcd1:2379,etcd2:2379,etcd3:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 10
    maximum_lag_on_failover: 1048576
```

### Application Failover

**Circuit Breaker Pattern:**
```python
from pybreaker import CircuitBreaker

db_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)

@db_breaker
async def query_database():
    # Database query with circuit breaker
    pass
```

---

## Monitoring HA

### Key Metrics

| Metric | Target | Alert |
|--------|--------|-------|
| Uptime | 99.9% | <99.5% |
| Failover Time | <30s | >60s |
| Replica Lag | <1s | >5s |
| Healthy Instances | ≥2 | <2 |

### Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: high-availability
    rules:
      - alert: InstanceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Instance {{ $labels.instance }} down"
      
      - alert: HighReplicaLag
        expr: pg_replication_lag > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High replication lag: {{ $value }}s"
      
      - alert: LowHealthyInstances
        expr: sum(up{job="backend"}) < 2
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Less than 2 healthy backend instances"
```

---

*High Availability Configuration Version: 1.0*
*Last Updated: 2026-03-14*
