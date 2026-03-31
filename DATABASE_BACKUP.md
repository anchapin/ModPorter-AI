# Database Backup and Restore Guide

This document describes backup and restore procedures for ModPorter-AI's PostgreSQL database.

## Overview

ModPorter-AI uses PostgreSQL with pgvector extension for:
- Conversion job metadata
- User feedback and analytics
- Document embeddings for RAG
- Behavioral testing data

## Backup Methods

### 1. Manual Full Backup

```bash
# Create a full backup of the ModPorter database
pg_dump -h localhost -U postgres -d modporter -Fc -f modporter_backup_$(date +%Y%m%d_%H%M%S).dump

# Or with compression
pg_dump -h localhost -U postgres -d modporter -Fc | gzip > modporter_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 2. Docker Environment Backup

```bash
# Backup from the docker-compose postgres container
docker compose exec postgres pg_dump -U postgres -d modporter -Fc > modporter_backup_$(date +%Y%m%d_%H%M%S).dump

# With compression
docker compose exec postgres pg_dump -U postgres -d modporter | gzip > modporter_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 3. Point-in-Time Recovery (PITR)

For production environments, enable Point-in-Time Recovery:

```bash
# In postgresql.conf (Docker: environment variable)
POSTGRES_INITDB_ARGS: --encoding=UTF-8 --lc-collate=C --lc-ctype=C
# Note: PITR requires WAL archiving configured
```

**Note:** PITR configuration requires:
1. WAL (Write-Ahead Log) archiving to external storage
2. Continuous backup infrastructure
3. Recovery point objective (RPO) configuration

For production, consider using:
- **AWS RDS** with automated backups
- **Supabase** with built-in PITR
- **CloudSQL** with PITR enabled

## Restore Procedures

### 1. Restore from Full Backup

```bash
# Restore to existing database (drops existing data)
pg_restore -h localhost -U postgres -d modporter -c modporter_backup.dump

# Restore to new database
createdb -h localhost -U postgres modporter_new
pg_restore -h localhost -U postgres -d modporter_new modporter_backup.dump
```

### 2. Docker Environment Restore

```bash
# Stop the backend to prevent writes
docker compose stop backend

# Restore
docker compose exec -T postgres pg_restore -U postgres -d modporter -c < backup.dump

# Restart backend
docker compose start backend
```

### 3. Selective Restore (Specific Tables)

```bash
# Extract specific tables from backup
pg_restore -h localhost -U postgres -d modporter -t conversion_jobs modporter_backup.dump

# Restore only data (no schema)
pg_restore -h localhost -U postgres -d modporter --data-only -t conversion_jobs modporter_backup.dump
```

## Automated Backups

### Cron-based Daily Backup

```bash
# Add to crontab (crontab -e)
# Daily backup at 2 AM
0 2 * * * docker compose exec postgres pg_dump -U postgres -d modporter -Fc | gzip > /backups/modporter_$(date +\%Y\%m\%d).sql.gz

# Keep last 7 days
0 2 * * * find /backups -name "modporter_*.sql.gz" -mtime +7 -delete
```

### Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: modporter-backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15
            command:
            - /bin/sh
            - -c
            - pg_dump -h postgres -U postgres -d modporter -Fc | gzip > /backups/modporter_$(date +%Y%m%d).sql.gz
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
          restartPolicy: OnFailure
```

## Backup Verification

```bash
# Verify backup integrity
pg_restore --version  # Check pg_dump version matches PostgreSQL version

# List contents of backup
pg_restore -l modporter_backup.dump | head -20

# Test restore to temporary database
createdb -h localhost -U postgres modporter_test
pg_restore -h localhost -U postgres -d modporter_test modporter_backup.dump
# Verify tables exist
psql -h localhost -U postgres -d modporter_test -c "\dt"
dropdb -h localhost -U postgres modporter_test
```

## Embeddings Backup (pgvector)

The `document_embeddings` table uses pgvector. When restoring:

```bash
# Verify vector extension exists
psql -h localhost -U postgres -d modporter -c "SELECT * FROM pg_extension WHERE extname='vector';"

# If not, create it
psql -h localhost -U postgres -d modporter -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## Disaster Recovery Checklist

1. **Pre-incident:**
   - [ ] Verify backup schedule is running
   - [ ] Test restore procedure in non-production
   - [ ] Document recovery time objective (RTO)
   - [ ] Document recovery point objective (RPO)

2. **During incident:**
   - [ ] Stop application writes
   - [ ] Create final backup (if possible)
   - [ ] Document timeline

3. **Post-incident:**
   - [ ] Restore to verified backup
   - [ ] Verify data integrity
   - [ ] Resume application
   - [ ] Document lessons learned

## Retention Policy

| Backup Type | Retention | Storage |
|-------------|-----------|---------|
| Daily | 7 days | Local |
| Weekly | 4 weeks | Local + S3 |
| Monthly | 12 months | S3/Glacier |
| Yearly | 7 years | S3/Glacier |

## Monitoring

Monitor backup success/failure:

```bash
# Check last backup timestamp
ls -la /backups/modporter_*.sql.gz | tail -1

# Add to monitoring (Prometheus AlertManager example)
- alert: BackupFailed
  expr: backup_last_success_timestamp{job="modporter-backup"} < time() - 86400
  for: 1h
  labels:
    severity: critical
  annotations:
    summary: "ModPorter backup has not succeeded in 24 hours"
```

## Related Documentation

- [SECURITY.md](./SECURITY.md) - Security policies
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Local development setup
- [Monitoring Setup](../monitoring/) - Prometheus/Grafana configuration
