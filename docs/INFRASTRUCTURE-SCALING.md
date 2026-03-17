# Infrastructure Scaling Plan

**ModPorter AI - Scale Preparation**

---

## Scaling Overview

This document outlines the infrastructure scaling strategy for ModPorter AI from beta (50 users) to production (10,000+ users).

---

## User Tiers & Projections

| Tier | Users | Conversions/Day | Infrastructure |
|------|-------|-----------------|----------------|
| **Beta** | 50 | 100 | Single VPS |
| **Launch** | 500 | 1,000 | Load balanced VPS |
| **Growth** | 5,000 | 10,000 | Multi-region |
| **Scale** | 50,000+ | 100,000+ | Cloud-native |

---

## Scaling Triggers

### Beta → Launch (50 → 500 users)

**Triggers:**
- 80%+ resource utilization sustained
- Conversion queue >50 pending
- Response time p95 >1s

**Actions:**
- Upgrade VPS (4CPU → 8CPU, 8GB → 16GB RAM)
- Add Redis cluster
- Enable CDN for static assets
- Implement connection pooling

### Launch → Growth (500 → 5,000 users)

**Triggers:**
- 80%+ resource utilization sustained
- Conversion queue >200 pending
- Response time p95 >2s

**Actions:**
- Load balancer with 2-3 backend instances
- Database read replicas
- Dedicated AI inference servers
- Multi-AZ deployment

### Growth → Scale (5,000 → 50,000+ users)

**Triggers:**
- Geographic latency issues
- Regional compliance requirements
- 99.9% uptime SLA requirement

**Actions:**
- Multi-region deployment (US, EU, Asia)
- Kubernetes orchestration
- Auto-scaling groups
- Global CDN
- Dedicated GPU clusters

---

## Component Scaling

### Frontend (React + Nginx)

**Current:** Single instance
**Scale:** CDN + multiple edge instances

| Users | Instances | CDN | Notes |
|-------|-----------|-----|-------|
| 50-500 | 1 | Cloudflare | Cache static assets |
| 500-5K | 2 | Cloudflare | Load balanced |
| 5K-50K | 3-5 | Cloudflare | Auto-scaling |
| 50K+ | Auto-scale | Cloudflare | Edge computing |

**Scaling Commands:**
```bash
# Add frontend instance
docker-compose up -d --scale frontend=3

# Enable CDN caching
# Cloudflare: Page Rules → Cache Everything
```

### Backend (FastAPI)

**Current:** Single instance
**Scale:** Load balanced instances with auto-scaling

| Users | Instances | CPU | RAM | Notes |
|-------|-----------|-----|-----|-------|
| 50-500 | 1 | 4 | 8GB | Current setup |
| 500-5K | 2-3 | 4 | 8GB | Load balanced |
| 5K-50K | 5-10 | 8 | 16GB | Auto-scaling |
| 50K+ | Auto-scale | 8 | 16GB | Kubernetes |

**Scaling Commands:**
```bash
# Add backend instances
docker-compose up -d --scale backend=3

# Kubernetes auto-scaling
kubectl autoscale deployment backend --min=3 --max=10 --cpu-percent=80
```

### AI Engine (CrewAI + Models)

**Current:** Single CPU instance
**Scale:** Dedicated GPU instances

| Users | Instances | GPU | Notes |
|-------|-----------|-----|-------|
| 50-500 | 1 CPU | None | Current setup |
| 500-5K | 2 CPU + 1 GPU | A10G | Modal for GPU |
| 5K-50K | 4 CPU + 2-4 GPU | A100 | Dedicated GPU servers |
| 50K+ | Auto-scale GPU | A100/H100 | GPU cluster |

**GPU Options:**
| Provider | GPU | Cost/Hour | Conversions/Hour |
|----------|-----|-----------|------------------|
| Modal | A10G | $0.70 | ~20 |
| RunPod | A100 | $1.50 | ~50 |
| AWS | A100 | $3.00 | ~50 |
| GCP | H100 | $4.00 | ~80 |

**Scaling Commands:**
```bash
# Enable GPU inference
export GPU_ENABLED=true
docker-compose -f docker-compose.gpu.yml up -d

# Modal scaling (automatic)
# Configure in modal_deployment.py
@stub.cls(gpu="A10G", allow_concurrent_inputs=10)
```

### Database (PostgreSQL + pgvector)

**Current:** Single instance
**Scale:** Primary + read replicas

| Users | Configuration | Storage | Notes |
|-------|---------------|---------|-------|
| 50-500 | Single | 80GB SSD | Current setup |
| 500-5K | Primary + 1 replica | 200GB SSD | Read scaling |
| 5K-50K | Primary + 3 replicas | 500GB SSD | Multi-AZ |
| 50K+ | Managed (RDS/Aurora) | Auto | Auto-scaling storage |

**Scaling Commands:**
```bash
# Add read replica (manual for now)
# In production, use managed service
docker-compose up -d postgres-replica

# Configure read/write splitting
# backend: Write to primary
# Analytics: Read from replica
```

### Redis (Caching + Queue)

**Current:** Single instance
**Scale:** Redis Cluster

| Users | Configuration | Memory | Notes |
|-------|---------------|--------|-------|
| 50-500 | Single | 512MB | Current setup |
| 500-5K | Single | 2GB | Increased memory |
| 5K-50K | Sentinel | 4GB | High availability |
| 50K+ | Cluster | 8GB+ | Sharded |

**Scaling Commands:**
```bash
# Increase Redis memory
docker-compose exec redis redis-cli CONFIG SET maxmemory 2gb

# Enable Redis Cluster (production)
# Requires 6 nodes (3 master + 3 replica)
```

---

## Load Balancing

### Current (Beta)
- Nginx on single VPS
- Simple round-robin

### Launch (500-5K users)
- HAProxy or Nginx Plus
- Health checks
- Sticky sessions for WebSocket

### Scale (5K+ users)
- AWS ALB / Cloudflare Load Balancing
- Geographic routing
- Auto-scaling integration

**HAProxy Configuration:**
```haproxy
frontend http_front
    bind *:80
    default_backend http_back

backend http_back
    balance roundrobin
    option httpchk GET /api/v1/health
    server backend1 backend:8000 check
    server backend2 backend:8000 check
    server backend3 backend:8000 check
```

---

## Monitoring at Scale

### Metrics to Track

**Infrastructure:**
- CPU utilization (target: <70%)
- Memory utilization (target: <80%)
- Disk I/O (target: <70%)
- Network throughput

**Application:**
- Request rate (req/s)
- Response time (p50, p95, p99)
- Error rate (target: <0.1%)
- Queue depth

**Business:**
- Conversions/hour
- Cost/conversion
- User satisfaction
- Active users

### Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU | >70% | >90% | Scale up |
| Memory | >80% | >95% | Scale up |
| Error Rate | >1% | >5% | Investigate |
| Response Time p95 | >1s | >3s | Optimize |
| Queue Depth | >50 | >200 | Scale workers |

---

## Disaster Recovery

### Backup Strategy

| Component | Frequency | Retention | Storage |
|-----------|-----------|-----------|---------|
| Database | Daily | 30 days | S3 + local |
| Config files | Weekly | 90 days | Git + S3 |
| User uploads | Daily | 7 days | S3 |

### Recovery Time Objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| Single instance failure | 5 min | 0 |
| Database failure | 15 min | 1 hour |
| Region failure | 1 hour | 4 hours |
| Complete outage | 4 hours | 24 hours |

---

## Cost Projections

### Monthly Infrastructure Costs

| Users | Frontend | Backend | AI/ML | Database | Total |
|-------|----------|---------|-------|----------|-------|
| 50 (Beta) | $20 | $40 | $150 | $20 | $230 |
| 500 (Launch) | $40 | $80 | $300 | $40 | $460 |
| 5K (Growth) | $100 | $200 | $1,000 | $100 | $1,400 |
| 50K (Scale) | $500 | $1,000 | $5,000 | $500 | $7,000 |

### Cost per Conversion

| Users | Conversions/Day | Cost/Day | Cost/Conversion |
|-------|-----------------|----------|-----------------|
| 50 | 100 | $7.67 | $0.077 |
| 500 | 1,000 | $15.33 | $0.015 |
| 5K | 10,000 | $46.67 | $0.005 |
| 50K | 100,000 | $233.33 | $0.002 |

**Economies of scale: 38x cost reduction per conversion**

---

## Implementation Checklist

### Beta → Launch

- [ ] Upgrade VPS resources
- [ ] Enable CDN (Cloudflare)
- [ ] Configure Redis persistence
- [ ] Set up monitoring alerts
- [ ] Document scaling procedures

### Launch → Growth

- [ ] Deploy load balancer
- [ ] Add backend instances
- [ ] Configure database replicas
- [ ] Enable auto-scaling
- [ ] Multi-AZ deployment

### Growth → Scale

- [ ] Kubernetes migration
- [ ] Multi-region deployment
- [ ] GPU cluster setup
- [ ] Global CDN configuration
- [ ] 99.9% SLA implementation

---

*Infrastructure Scaling Plan Version: 1.0*
*Last Updated: 2026-03-14*
