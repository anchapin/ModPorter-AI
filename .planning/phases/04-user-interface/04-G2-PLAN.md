# Plan 04-G2: Beta Launch Infrastructure

**Plan ID**: 04-G2  
**Phase**: 04-User-Interface  
**Milestone**: v1.0: Public Beta  
**Type**: Gap Closure - Infrastructure Setup  
**Status**: ✅ Completed  
**Created**: 2026-03-18
**Completed**: 2026-03-18

---

## Objective

Prepare infrastructure for beta launch: Discord server, analytics dashboard, error alerting, and feedback collection system.

---

## Success Criteria

- [ ] Discord server with 5+ channels operational
- [ ] Analytics dashboard page accessible in frontend
- [ ] Error alerting configured at 5% threshold
- [ ] Post-conversion feedback survey implemented
- [ ] Beta launch announcement content ready
- [ ] User registration tracking in place

---

## Requirements Mapped

| REQ-ID | Description | Coverage |
|--------|-------------|----------|
| REQ-1.15 | Monitoring & Analytics | Full implementation |
| REQ-1.15.1 | Error Alerting | Configuration |
| REQ-1.15.2 | Feedback Collection | Survey implementation |
| REQ-1.16 | User Documentation | Launch content |

---

## Dependencies

| Plan | Dependency | Status |
|------|------------|--------|
| 04-G1 | Pricing page needed | ⚠️ Check first |

---

## Tasks

### Task 04-G2.1: Discord Server Setup

**Type**: Setup  
**Effort**: Low (2 hours)  
**Dependencies**: None  
**Verification**: Discord server accessible with 5+ channels

**Description**: Create Discord server structure for community support.

**Steps**:
1. Create Discord server "ModPorter-AI Community"
2. Configure channels:
   - `#announcements` - Launch updates, feature releases
   - `#general` - General discussion
   - `#support` - Technical help
   - `#feedback` - User suggestions
   - `#showcase` - Converted mod showcases
3. Set up roles: Admin, Moderator, Beta Tester, Member
4. Configure bot permissions
5. Create invite link

**Files to Create**:
- Discord server configuration documentation

---

### Task 04-G2.2: Analytics Dashboard Page

**Type**: Implementation  
**Effort**: Medium (4 hours)  
**Dependencies**: None  
**Verification**: Dashboard page renders at `/analytics`

**Description**: Create dedicated analytics dashboard page in frontend.

**Steps**:
1. Check existing analytics components in frontend
2. Create new `/analytics` route in React Router
3. Implement dashboard components:
   - Conversion stats card (count, success rate)
   - User metrics card (registrations, active users)
   - Error rate card (current %, trend)
   - Performance metrics card (avg time, throughput)
4. Connect to backend API endpoints
5. Add real-time refresh (30s interval)
6. Style with existing design system

**Files to Create/Modify**:
- `frontend/src/pages/Analytics.tsx` (new)
- `frontend/src/components/Analytics/` (new directory)
- `frontend/src/api/analytics.ts` (new or extend)

**API Endpoints Needed**:
- `GET /api/v1/analytics/conversions`
- `GET /api/v1/analytics/users`
- `GET /api/v1/analytics/errors`

---

### Task 04-G2.3: Error Alerting Configuration

**Type**: Configuration  
**Effort**: Low (2 hours)  
**Dependencies**: Task 04-G2.2 (analytics data)  
**Verification**: Test alert triggers at 5% threshold

**Description**: Configure error alerting thresholds and notification system.

**Steps**:
1. Review existing error tracking (check backend for Sentry/DataDog)
2. Configure alerting rules:
   - Error rate > 5% triggers alert
   - Latency > 30s triggers alert
   - Conversion failure > 10% triggers alert
3. Set up notification channels:
   - Discord webhook for alerts
   - Email for critical issues
4. Create alert history log
5. Test with simulated error spike

**Files to Modify**:
- Backend alerting configuration
- Discord webhook setup

---

### Task 04-G2.4: Post-Conversion Feedback Survey

**Type**: Implementation  
**Effort**: Medium (3 hours)  
**Dependencies**: None  
**Verification**: Survey appears after successful conversion

**Description**: Implement feedback collection survey shown after conversions.

**Steps**:
1. Create survey component in frontend:
   - Rating (1-5 stars)
   - Conversion quality question
   - Ease of use question
   - Open feedback text area
   - Submit button
2. Add to conversion results page
3. Create backend endpoint: `POST /api/v1/feedback`
4. Store feedback in database
5. Add to admin dashboard for viewing
6. Test submission flow

**Files to Create/Modify**:
- `frontend/src/components/FeedbackSurvey.tsx` (new)
- `backend/src/api/feedback.py` (new)
- Database model for feedback

---

### Task 04-G2.5: Beta Launch Announcement Content

**Type**: Content Creation  
**Effort**: Low (2 hours)  
**Dependencies**: None  
**Verification**: Content ready for publication

**Description**: Create launch announcement content for public beta.

**Steps**:
1. Draft blog post announcing beta
2. Create social media copy (Twitter, Reddit)
3. Write email announcement for waitlist
4. Prepare FAQ for launch day
5. Create screenshots/demos for content

**Deliverables**:
- `docs/launch/announcement-blog.md`
- `docs/launch/social-media-copy.md`
- `docs/launch/email-waitlist.md`

---

### Task 04-G2.6: User Registration Tracking

**Type**: Implementation  
**Effort**: Low (2 hours)  
**Dependencies**: None  
**Verification**: Registration count visible in dashboard

**Description**: Set up tracking for beta user registrations to meet 100-user goal.

**Steps**:
1. Review existing user registration flow
2. Add registration timestamp tracking
3. Create "Beta User" flag in database
4. Add registration metrics to analytics:
   - Total registrations
   - Daily/weekly signups
   - Conversion source tracking
5. Create milestone notification at 25, 50, 75, 100 users

**Files to Modify**:
- Backend user model
- Analytics dashboard

---

## Wave Grouping

| Wave | Tasks | Description |
|------|-------|-------------|
| 1 | 04-G2.1 | Discord server setup (independent) |
| 2 | 04-G2.2, 04-G2.3 | Dashboard + alerting (parallel) |
| 3 | 04-G2.4, 04-G2.5, 04-G2.6 | Survey + content + tracking (parallel) |

---

## Verification

### Checkpoint 1: Discord Ready
- [ ] Server created with invite link
- [ ] All 5 channels exist
- [ ] Roles configured

### Checkpoint 2: Dashboard Live
- [ ] `/analytics` route accessible
- [ ] Data populating (can use mock data)
- [ ] Responsive on mobile

### Checkpoint 3: Alerts Working
- [ ] Test alert triggers correctly
- [ ] Discord webhook receives test message

### Checkpoint 4: Survey Active
- [ ] Survey shows after conversion
- [ ] Data saves to database
- [ ] Admin can view submissions

### Checkpoint 5: Launch Ready
- [ ] All content drafted
- [ ] Registration tracking active

---

## Human Verify Signal

Reply: "Plan 04-G2 verified - Beta launch infrastructure ready"

---

## Notes

- **External Dependency**: Discord server creation may require manual Discord UI login
- **Automation**: Error alerting and analytics can be automated without manual intervention
- **Prerequisite**: Check if Plan 04-G1 (pricing page) is complete before launch

---

*Plan created: 2026-03-18 - Gap closure from 04-GAP-PLAN.md*
