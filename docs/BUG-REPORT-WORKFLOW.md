# Bug Report Workflow

**ModPorter AI Beta Program**

---

## Bug Report Process

### User Submission Flow

```
1. User encounters bug
   ↓
2. Submits bug report (UI or Discord)
   ↓
3. Auto-acknowledgment sent
   ↓
4. Triage by support team
   ↓
5. Assigned to developer
   ↓
6. Fix developed and tested
   ↓
7. Deployed to production
   ↓
8. User notified of fix
```

---

## Bug Report Template

### Required Information

**Basic Info:**
- Title (clear, concise description)
- Description (what happened)
- Severity (low, medium, high, critical)
- Conversion ID (if applicable)

**Technical Details:**
- Steps to reproduce
- Expected behavior
- Actual behavior
- Browser/OS (if web issue)
- Mod file (if conversion issue)

**Optional:**
- Screenshots/videos
- Log files
- Workarounds found

---

## Severity Levels

### Critical 🔴
**Definition:** Complete service outage or data loss

**Examples:**
- Service completely down
- All conversions failing
- User data lost/corrupted
- Security vulnerability

**Response Time:** < 4 hours
**Fix Target:** < 24 hours

### High 🟠
**Definition:** Major feature broken

**Examples:**
- Conversion fails for specific mod types
- Download not working
- Login issues
- Payment processing errors

**Response Time:** < 24 hours
**Fix Target:** < 72 hours

### Medium 🟡
**Definition:** Minor feature broken, workaround exists

**Examples:**
- UI elements misaligned
- Slow performance
- Non-critical feature not working
- Minor visual bugs

**Response Time:** < 48 hours
**Fix Target:** < 1 week

### Low 🟢
**Definition:** Cosmetic issue or minor inconvenience

**Examples:**
- Typos in UI
- Color inconsistencies
- Minor UX improvements
- Feature requests

**Response Time:** < 1 week
**Fix Target:** Next release

---

## Bug Report Channels

### Discord (#bug-reports)

**Format:**
```
**Title:** [Brief description]
**Severity:** [low/medium/high/critical]
**Conversion ID:** [if applicable]
**Description:** [What happened]
**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Step 3]
**Expected:** [What should happen]
**Actual:** [What actually happened]
```

**Response:** Bot auto-acknowledges, support team responds within SLA

### Web Form (In-App)

**Location:** Settings → Help → Report a Bug

**Fields:**
- Title (required)
- Description (required)
- Severity (dropdown)
- Conversion ID (auto-filled if reporting from conversion)
- Attach files (screenshots, logs)
- Email for follow-up

**Response:** Auto-ticket created, email confirmation sent

### Email (beta@modporter.ai)

**Subject Format:** `[Bug] [Severity] Brief description`

**Example:** `[Bug] [High] Conversion fails for Fabric mods`

**Response:** Auto-reply with ticket number, manual response within SLA

---

## Triage Process

### Step 1: Auto-Categorization

**Bot assigns:**
- Severity (based on keywords)
- Category (conversion, UI, account, etc.)
- Priority score

### Step 2: Support Review

**Support team:**
- Verifies severity
- Adds missing information
- Reproduces if possible
- Assigns to appropriate developer

### Step 3: Developer Assignment

**Based on category:**
- Conversion issues → AI/ML team
- UI bugs → Frontend team
- API issues → Backend team
- Infrastructure → DevOps team

---

## Bug Tracking States

```
NEW → TRIAGED → IN_PROGRESS → IN_REVIEW → FIXED → VERIFIED → CLOSED
         ↓
      CANNOT_REPRODUCE → NEEDS_INFO
         ↓
      WONT_FIX → DUPLICATE
```

### State Descriptions

| State | Description |
|-------|-------------|
| **NEW** |刚 submitted, not yet reviewed |
| **TRIAGED** | Reviewed, categorized, assigned |
| **IN_PROGRESS** | Developer working on fix |
| **IN_REVIEW** | Fix submitted, under review |
| **FIXED** | Fix deployed to production |
| **VERIFIED** | User confirmed fix works |
| **CLOSED** | Issue resolved, closed |
| **CANNOT_REPRODUCE** | Unable to reproduce bug |
| **NEEDS_INFO** | Waiting for more information |
| **WONT_FIX** | Decided not to fix (with reason) |
| **DUPLICATE** | Already reported |

---

## Communication Templates

### Auto-Acknowledgment

```
Thanks for reporting this bug!

Ticket ID: BUG-12345
Severity: [severity]
Expected Response: [timeframe based on severity]

Our team will review your report and get back to you soon.

In the meantime:
- Check status: https://modporter.ai/bugs/BUG-12345
- Add more info: Reply to this email

Thanks for helping us improve!
```

### Status Update

```
Update on Bug BUG-12345

Status: [NEW_STATUS]
Assigned to: [Developer name]
Expected fix: [date]

[Optional: Additional details about progress]

Track progress: https://modporter.ai/bugs/BUG-12345
```

### Fix Notification

```
Good news! Bug BUG-12345 has been fixed.

What was fixed:
[Brief description of the fix]

Please try again and let us know if you still experience issues.

Thanks for your patience!
```

---

## Metrics & SLAs

### Response Time SLAs

| Severity | Acknowledge | First Response | Resolution |
|----------|-------------|----------------|------------|
| Critical | < 30 min | < 1 hour | < 24 hours |
| High | < 4 hours | < 8 hours | < 72 hours |
| Medium | < 24 hours | < 48 hours | < 1 week |
| Low | < 48 hours | < 1 week | Next release |

### Tracking Metrics

**Weekly:**
- Bugs reported
- Bugs resolved
- Average time to resolution
- Bugs by severity
- Bugs by category

**Monthly:**
- Bug recurrence rate
- User satisfaction with bug handling
- Top bug categories
- Team performance vs SLA

---

## GitHub Integration

### Auto-Creation

Bug reports automatically create GitHub issues:

**Label Mapping:**
- Severity → priority-critical/high/medium/low
- Category → bug-conversion, bug-ui, bug-api, etc.
- Status → status-triaged, status-in-progress, etc.

### Template

```markdown
## Bug Report

**Reported by:** @username
**Severity:** [severity]
**Conversion ID:** [if applicable]

### Description
[Description from bug report]

### Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happened]

### Environment
- OS: [OS]
- Browser: [Browser]
- Mod file: [Attached/Link]

### Additional Context
[Any screenshots, logs, or other info]

---
**Ticket:** BUG-12345
**Reported:** [Date]
```

---

## Escalation Process

### When to Escalate

**Escalate to Lead if:**
- SLA breached
- User requests escalation
- Bug affects multiple users
- Critical security issue
- High-profile user affected

**Escalation Path:**
1. Support Team Member
2. Support Lead
3. Engineering Lead
4. CTO/Founder

### Escalation Template

```
ESCALATION: BUG-12345

Original Report: [Date/Time]
Current Status: [Status]
Issue: [Why escalating]
Requested Action: [What we need]
User Impact: [Who's affected]

[Link to full bug report]
```

---

*Bug Report Workflow Version: 1.0*
*Last Updated: 2026-03-14*
