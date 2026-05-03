# PortKit Incident Response Runbook

**Issue**: [#1211](https://github.com/anchapin/portkit/issues/1211)

## Overview

This runbook defines PortKit's incident response process for production incidents during beta and post-launch. It answers three questions:
1. How do I know something is broken?
2. What do I do when it breaks?
3. How do I communicate to users during an incident?

---

## 1. Severity Levels

| Level | Definition | Response SLA | Example |
|-------|-----------|--------------|---------|
| **P0 — Critical** | Service is down or data is at risk | Respond within 15 min, 24/7 | API returns 5xx to all users; DB unreachable; Stripe webhooks failing |
| **P1 — High** | Core feature broken for a subset of users | Respond within 1 hour during waking hours | Conversion pipeline stalled; auth broken for new signups |
| **P2 — Medium** | Non-core feature degraded | Next business day | Conversion report PDF export failing; email notifications delayed |
| **P3 — Low** | Cosmetic / minor UX issue | Next planned sprint | Landing page typo; dark mode rendering glitch |

---

## 2. Alert Sources and Response

| Alert Source | Tool | Triggers On | First Action |
|-------------|------|-------------|--------------|
| Uptime monitor | Better Stack / UptimeRobot | API endpoint down | Check Fly.io dashboard → `flyctl status` → check app logs |
| Error rate spike | Sentry | 5xx error rate > 5% in 5 min | Review Sentry error feed → check recent deploy → rollback if needed |
| Celery queue depth | Flower / custom metric | Queue depth > 100 jobs for > 5 min | Check worker logs → scale workers → check for stuck jobs |
| LLM cost spike | OpenRouter / custom | Daily spend > $X | Check for runaway retry loops → disable LLM conversion feature flag |
| Payment failures | Stripe webhook | Consecutive failed payment | Check Stripe dashboard → verify webhook endpoint health |
| DB connection failures | Sentry / Fly.io | `asyncpg` connection errors | Check Fly.io Postgres status → restart DB proxy if needed |
| Disk / memory pressure | Fly.io metrics | Memory > 90% | Scale VM → identify memory leak → restart worker |

### First-Response Checklist

1. **Acknowledge** the alert within SLA window
2. **Assess** severity and impact
3. **Communicate** on status page if P0/P1
4. **Diagnose** using runbooks below
5. **Resolve** and verify recovery
6. **Document** in post-mortem if P0/P1

---

## 3. Runbooks Per Failure Mode

### Runbook: API is Returning 5xx

1. Check Fly.io status page (status.fly.io) for platform-level incidents
2. `flyctl logs -a portkit-api` — look for exception traceback
3. Check recent deploys: `flyctl releases -a portkit-api`
4. If caused by a deploy: `flyctl deploy --image <previous-image-tag>` to roll back
5. Verify recovery: hit `/health` endpoint, check Sentry error rate drops
6. File a post-mortem in `docs/post-mortems/YYYY-MM-DD-[short-title].md`

### Runbook: Conversion Pipeline Stalled (Jobs Not Processing)

1. Check Celery worker status (Flower dashboard or `celery inspect active`)
2. Check Redis connectivity: `redis-cli ping`
3. Check for stuck jobs: `celery inspect reserved`
4. Restart workers if unresponsive: `flyctl restart -a portkit-worker`
5. Check for DB connection exhaustion (asyncpg pool limit hit)
6. Verify recovery: submit a test conversion job, monitor queue depth

### Runbook: Database Unreachable

1. Check Fly.io Postgres status: `flyctl status -a portkit-db`
2. Check connection string / secrets: `flyctl secrets list -a portkit-api`
3. Restart Postgres proxy: `flyctl postgres restart -a portkit-db`
4. If data loss suspected: verify latest backup timestamp, initiate restore if needed
5. Notify affected users if downtime > 5 minutes

### Runbook: Stripe Webhook Failures

1. Check Stripe dashboard → Developers → Webhooks → recent delivery attempts
2. Verify endpoint is reachable: `curl -X POST https://portkit.ai/api/webhooks/stripe`
3. Replay failed webhook events from the Stripe dashboard
4. If subscription state is inconsistent: use Stripe dashboard to manually correct

### Runbook: Security Incident (Suspected Breach / Unauthorized Access)

1. Immediately rotate all secrets: `flyctl secrets set ...` for all credentials
2. Revoke and reissue all API keys (Stripe, OpenRouter, etc.)
3. Review access logs for the past 24-48 hours
4. Notify affected users within 72 hours (GDPR requirement)
5. Document the incident in `docs/post-mortems/`

---

## 4. Communication Templates

### Status Page Incident Template

```
[HH:MM ET] Investigating reports of [issue description]. Updates every 30 minutes.
[HH:MM ET] Identified: [root cause]. Working on fix.
[HH:MM ET] Fix deployed. Monitoring for full recovery.
[HH:MM ET] Resolved. [brief summary of impact and fix]. Post-mortem to follow.
```

### Email to Affected Beta Users (P0/P1 Incidents)

```
Subject: PortKit service disruption — [date]

We experienced [brief description] from [start time] to [end time] ET.

Impact: [what was affected — conversions, login, etc.]
Root cause: [one sentence]
What we did: [one sentence]
What we're doing to prevent recurrence: [one sentence]

We're sorry for the disruption. Your in-progress conversions [status].

— Alex @ PortKit
```

---

## 5. Post-Mortem Template

File in `docs/post-mortems/YYYY-MM-DD-[title].md`:

- **Date/time**: When did it start? When was it resolved?
- **Impact**: How many users affected? How long?
- **Root cause**: The actual technical cause (not symptoms)
- **Timeline**: Detection → first response → diagnosis → resolution (with timestamps)
- **What went well**: What helped contain or resolve the incident
- **What went wrong**: What made it harder
- **Action items**: Specific follow-up issues filed (link to GitHub issues)

---

## 6. Fly.io Alert Configuration

Configure the following alert rules in Fly.io:

| Metric | Threshold | Severity |
|--------|-----------|----------|
| CPU | > 90% for 5m | P1 |
| Memory | > 90% for 5m | P1 |
| Error rate | > 5% in 5m | P0 |
| Disk | > 85% | P2 |

---

## Related Documentation

- **Status Page**: See [#1153](https://github.com/anchapin/portkit/issues/1153) for public status page
- **Error Monitoring**: Sentry integration per [#1150](https://github.com/anchapin/portkit/issues/1150)
- **Post-Mortems**: See `docs/post-mortems/` directory