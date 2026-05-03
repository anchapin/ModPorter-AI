# Database Backup and Disaster Recovery

**portkit Database Infrastructure**

---

## Overview

portkit uses PostgreSQL 15 with pgvector extension for:
- Conversion job metadata and state
- User accounts and authentication
- User feedback and analytics
- Document embeddings for RAG
- Behavioral testing data

### Recovery Objectives

| Objective | Target | Description |
|-----------|--------|-------------|
| **RPO** | 24 hours | Maximum acceptable data loss |
| **RTO** | 4 hours | Maximum acceptable downtime |
| **Backup Frequency** | Daily | Full backups with WAL archival |

---

## Backup Strategy

### Backup Types

1. **Full Backups** (Daily)
   - Complete database dump in custom format
   - Compressed with gzip
   - Retention: 7 days (daily), 4 weeks (weekly), 12 months (monthly)

2. **WAL Archival** (Continuous)
   - Write-Ahead Log shipping for point-in-time recovery
   - Enables recovery to any point within the backup window

3. **Offsite Replication**
   - S3 bucket replication for disaster recovery
   - Standard_IA storage class for cost optimization

### Backup Schedule

```
00:00 UTC - Daily backup starts
01:00 UTC - WAL switch and verification
02:00 UTC - S3 upload
03:00 UTC - Cleanup of old backups
```

### Backup Retention

| Tier | Retention | Storage |
|------|------------|---------|
| Daily | 7 days | Local + S3 |
| Weekly | 4 weeks | S3 |
| Monthly | 12 months | S3/Glacier |
| Yearly | 7 years | S3/Glacier |

---

## Automated Backup System

### Backup Script

The backup system is automated via `scripts/portkit-backup.sh`:

```bash
# Daily backup (default)
./scripts/portkit-backup.sh daily

# Weekly backup
./scripts/portkit-backup.sh weekly

# Monthly backup
./scripts/portkit-backup.sh monthly

# List available backups
./scripts/portkit-backup.sh list

# Verify a backup
./scripts/portkit-backup.sh verify /path/to/backup.dump.gz
```

### Environment Variables

```bash
# Database connection
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=portkit
export PGUSER=postgres
export PGPASSWORD=your_password

# Backup configuration
export BACKUP_ROOT=/backups/postgres
export RETENTION_DAILY=7
export RETENTION_WEEKLY=4
export RETENTION_MONTHLY=12

# S3 configuration
export S3_BACKUP_BUCKET=your-bucket-name
export S3_PREFIX=postgres

# Notifications
export SLACK_WEBHOOK_URL=https://hooks.slack.com/...
```

### Cron Setup

Add to crontab for automated backups:

```bash
# Edit crontab
crontab -e

# Add these lines:
# Daily backup at midnight UTC
0 0 * * * /home/alex/Projects/portkit/scripts/portkit-backup.sh daily >> /var/log/portkit/backup.log 2>&1

# Weekly backup on Sunday at 1 AM UTC
0 1 * * 0 /home/alex/Projects/portkit/scripts/portkit-backup.sh weekly >> /var/log/portkit/backup.log 2>&1

# Monthly backup on 1st of month at 2 AM UTC
0 2 1 * * /home/alex/Projects/portkit/scripts/portkit-backup.sh monthly >> /var/log/portkit/backup.log 2>&1
```

---

## Point-in-Time Recovery (PITR)

### Prerequisites

1. WAL archiving must be enabled
2. Sufficient backup storage for WAL segments
3. Understanding of the target recovery point

### Recovery Process

1. **Identify the recovery point**
   ```bash
   # Check transaction logs
   ls -la /backups/postgres/wal_*.tar.gz
   ```

2. **Stop the application**
   ```bash
   docker compose stop backend celery-worker
   ```

3. **Restore from full backup**
   ```bash
   # Create new database
   createdb -h localhost -U postgres portkit_recovered

   # Restore full backup
   gunzip -c /backups/postgres/daily/full_20260401_120000.dump.gz | \
       pg_restore -h localhost -U postgres -d portkit_recovered --no-owner
   ```

4. **Apply WAL segments** (if needed)
   ```bash
   # For PITR, configure recovery.conf and apply WAL
   # See PostgreSQL documentation for details
   ```

5. **Verify the restore**
   ```bash
   psql -h localhost -U postgres -d portkit_recovered -c "SELECT count(*) FROM users;"
   psql -h localhost -U postgres -d portkit_recovered -c "SELECT count(*) FROM conversion_jobs;"
   ```

6. **Restart the application**
   ```bash
   docker compose start backend celery-worker
   ```

---

## Disaster Recovery Plan

### Recovery Scenarios

#### Scenario 1: Database Corruption

**Symptoms:**
- Database reports corruption errors
- Query failures with I/O errors
- Inconsistent data integrity

**Recovery Steps:**
1. Stop writes to the database immediately
2. Create a final backup of current state (if possible)
3. Identify the last known good backup
4. Restore from the most recent clean backup
5. Verify data integrity
6. Resume operations

**Estimated RTO:** 1-2 hours

#### Scenario 2: Complete Data Loss

**Symptoms:**
- Database volume destroyed
- Hardware failure
- Natural disaster

**Recovery Steps:**
1. Provision new database server
2. Restore from most recent S3 backup
3. Verify application connectivity
4. Resume operations
5. Document lessons learned

**Estimated RTO:** 2-4 hours

#### Scenario 3: Ransomware Attack

**Symptoms:**
- Database encrypted
- Backup files encrypted
- Ransom note received

**Recovery Steps:**
1. Isolate affected systems immediately
2. Do NOT pay the ransom
3. Restore from offline S3 backups (not connected to network)
4. Verify no malware in restored system
5. Resume operations
6. Report to authorities

**Estimated RTO:** 4-8 hours

### Disaster Recovery Checklist

#### Pre-Incident Preparation

- [ ] Daily backup cron job is configured and running
- [ ] Weekly/monthly backup cron jobs are configured
- [ ] S3 bucket is configured with proper permissions
- [ ] Backup verification tested successfully
- [ ] Recovery procedures documented and tested
- [ ] Recovery point objective (RPO) documented
- [ ] Recovery time objective (RTO) documented
- [ ] Contact list for incident response available
- [ ] Runbook for common scenarios available

#### During Incident

- [ ] Activate incident response team
- [ ] Assess extent of damage
- [ ] Stop writes to prevent data corruption
- [ ] Create final backup if possible
- [ ] Document timeline of events
- [ ] Communicate status to stakeholders

#### Post-Incident Recovery

- [ ] Verify backup integrity before restore
- [ ] Restore database to clean state
- [ ] Verify data integrity (row counts, checksums)
- [ ] Test application connectivity
- [ ] Resume read operations first
- [ ] Resume write operations after verification
- [ ] Monitor for anomalies
- [ ] Document lessons learned
- [ ] Update procedures based on findings

---

## Monitoring and Alerts

### Backup Monitoring

Monitor backup success/failure with Prometheus alerts defined in `prometheus/backup_rules.yml`:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Backup Success Rate | 100% | < 95% |
| Backup Age | < 24h | > 30h |
| Verification Pass | 100% | < 90% |
| S3 Upload Success | 100% | < 95% |

### Prometheus Alert Rules

Key alerts configured:
- `BackupTooOld`: Backup older than 24 hours
- `BackupVerificationFailed`: Backup verification failures
- `BackupUploadFailed`: S3 upload failures
- `PostgreSQLDown`: Database unavailable
- `PostgreSQLReplicationLag`: Replication lag > 5 seconds

---

## Backup Verification

### Manual Verification

```bash
# Check backup file exists
ls -la /backups/postgres/daily/

# Verify backup integrity
./scripts/portkit-backup.sh verify /backups/postgres/daily/full_20260401_120000.dump.gz

# List backup contents
pg_restore -l /backups/postgres/daily/full_20260401_120000.dump.gz | head -20

# Test restore to temporary database
createdb -h localhost -U postgres portkit_test
pg_restore -h localhost -U postgres -d portkit_test /backups/postgres/daily/full_20260401_120000.dump.gz
psql -h localhost -U postgres -d portkit_test -c "\dt"
dropdb -h localhost -U postgres portkit_test
```

### Automated Verification

The backup script automatically verifies:
1. Backup file creation
2. Compression integrity
3. Restore test (when possible)

---

## Restore Procedures

### Restore from Local Backup

```bash
# Stop the application
docker compose stop backend celery-worker

# Restore database
gunzip -c /backups/postgres/daily/full_20260401_120000.dump.gz | \
    pg_restore -h localhost -U postgres -d portkit --clean --no-owner

# Restart the application
docker compose start backend celery-worker
```

### Restore from S3 Backup

```bash
# Download from S3
aws s3 cp s3://your-bucket/postgres/daily/full_20260401_120000.dump.gz /tmp/

# Restore
gunzip -c /tmp/full_20260401_120000.dump.gz | \
    pg_restore -h localhost -U postgres -d portkit --clean --no-owner
```

### Selective Table Restore

```bash
# Extract specific tables from backup
pg_restore -h localhost -U postgres -d portkit -t conversion_jobs \
    /backups/postgres/daily/full_20260401_120000.dump.gz

# Restore only data (no schema)
pg_restore -h localhost -U postgres -d portkit --data-only -t users \
    /backups/postgres/daily/full_20260401_120000.dump.gz
```

---

## pgvector Extensions

The `document_embeddings` table uses pgvector. Ensure extension exists on restore:

```bash
# Verify vector extension
psql -h localhost -U postgres -d portkit -c \
    "SELECT * FROM pg_extension WHERE extname='vector';"

# Create if not exists
psql -h localhost -U postgres -d portkit -c \
    "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Related Documentation

- [HIGH-AVAILABILITY.md](./HIGH-AVAILABILITY.md) - HA configuration
- [SECURITY.md](./SECURITY.md) - Security policies
- [docker-compose.prod.yml](../docker-compose.prod.yml) - Production database config
- [prometheus/backup_rules.yml](../prometheus/backup_rules.yml) - Backup monitoring alerts

---

*Document Version: 2.0*
*Last Updated: 2026-05-03*
*Backup Script Version: 2.0.0*