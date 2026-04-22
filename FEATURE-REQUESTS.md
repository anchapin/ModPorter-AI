# Feature Request System

**Portkit Beta Program**

---

## Feature Request Process

### Submission Flow

```
1. User has idea
   ↓
2. Submits feature request
   ↓
3. Community votes/comments
   ↓
4. Product team reviews
   ↓
5. Prioritized for roadmap
   ↓
6. Development
   ↓
7. Beta testing
   ↓
8. Public release
```

---

## Submission Channels

### In-App (Recommended)

**Location:** Settings → Feature Requests

**Fields:**
- Title (required, 5-100 characters)
- Description (required, 20-2000 characters)
- Use case (required, why do you need this?)
- Priority (low, medium, high)
- Category (conversion, UI, integrations, etc.)
- Similar tools (optional, links to competitors)

**Benefits:**
- Auto-categorization
- Easy to track status
- Voting integrated
- Direct link to your request

### Discord (#feature-requests)

**Format:**
```
**Title:** [Feature name]
**Category:** [conversion/UI/integrations/etc.]
**Description:** [What you want]
**Use Case:** [Why you need it]
**Similar Tools:** [If any]
```

**Process:**
- Bot creates request from message
- Community reacts with 👍 to vote
- Product team reviews weekly

### Email (features@portkit.cloud)

**Subject:** `[Feature Request] Brief description`

**Body:**
- What you want
- Why you need it
- How you'd use it
- Any similar tools you've used

**Response:** Auto-acknowledgment with request ID

---

## Feature Categories

### Conversion
- New mod types supported
- Improved conversion accuracy
- Faster conversion speed
- Batch conversion
- Custom conversion rules

### User Interface
- Dashboard improvements
- New themes
- Mobile app
- Keyboard shortcuts
- Accessibility features

### Integrations
- Modrinth integration
- CurseForge integration
- GitHub integration
- Discord bot
- API access

### Account & Billing
- Team accounts
- Enterprise features
- SSO integration
- Usage reports
- Custom quotas

### Other
- Documentation improvements
- Tutorial requests
- Community features
- Partnership ideas

---

## Prioritization Framework

### RICE Scoring

**Reach:** How many users will this affect?
- 1: < 1% of users
- 2: 1-10% of users
- 3: 10-50% of users
- 4: > 50% of users

**Impact:** How much will this improve the experience?
- 0.25: Minimal impact
- 0.5: Minor impact
- 1: Moderate impact
- 2: High impact
- 3: Massive impact

**Confidence:** How sure are we about our estimates?
- 50%: Low confidence (guessing)
- 80%: Medium confidence (some data)
- 100%: High confidence (strong data)

**Effort:** How much work is this?
- 1: < 1 day
- 2: 1-3 days
- 3: 3-7 days
- 4: 1-2 weeks
- 5: > 2 weeks

**RICE Score:** (Reach × Impact × Confidence) / Effort

### Priority Levels

| Score | Priority | Timeline |
|-------|----------|----------|
| > 50 | Critical | Next sprint |
| 20-50 | High | This month |
| 10-20 | Medium | This quarter |
| < 10 | Low | Backlog |

---

## Feature Request States

```
SUBMITTED → UNDER_REVIEW → PLANNED → IN_PROGRESS → IN_TESTING → RELEASED
     ↓            ↓
  DUPLICATE   WON'T_DO
     ↓
  CLOSED
```

### State Descriptions

| State | Description |
|-------|-------------|
| **SUBMITTED** |刚 submitted, awaiting review |
| **UNDER_REVIEW** | Product team evaluating |
| **PLANNED** | Approved for roadmap |
| **IN_PROGRESS** | Currently being developed |
| **IN_TESTING** | In beta testing |
| **RELEASED** | Live in production |
| **DUPLICATE** | Already requested |
| **WON'T_DO** | Not planned (with reason) |

---

## Community Voting

### Voting System

**Upvote (👍):** Support this feature
**Comment:** Add context or use cases
**Share:** Spread the word

### Voting Weight

**Beta Testers:** 1 vote
**Active Contributors:** 2 votes (10+ feedback submissions)
**Founders:** 3 votes (first 50 beta users)

### Voting Thresholds

| Upvotes | Action |
|---------|--------|
| 10+ | Product team review |
| 25+ | Priority consideration |
| 50+ | Roadmap candidate |
| 100+ | High priority |

---

## Product Review Process

### Weekly Review

**When:** Every Monday
**Who:** Product team
**What:** Review new requests from past week

**Criteria:**
- Alignment with product vision
- Technical feasibility
- Resource requirements
- User impact
- Strategic value

### Monthly Roadmap Update

**When:** First week of each month
**What:** Publish updated roadmap

**Includes:**
- New features planned
- Features in progress
- Recently released features
- Won't do (with explanations)

---

## Communication Templates

### Acknowledgment

```
Thanks for your feature request!

Request ID: FEAT-12345
Title: [Feature title]
Status: Submitted

What happens next:
1. Our product team reviews your request
2. Community votes and comments
3. We update you on the status

Track your request: https://portkit.cloud/features/FEAT-12345

Thanks for helping us improve!
```

### Under Review

```
Update on Feature Request FEAT-12345

Status: Under Review

Our product team is now reviewing your request. We'll evaluate:
- User impact
- Technical feasibility
- Resource requirements

Expected decision: [Date]

Track progress: https://portkit.cloud/features/FEAT-12345
```

### Planned

```
Great news! Feature FEAT-12345 is planned!

Status: Planned
Target release: [Month/Quarter]

What's next:
1. Design and specification
2. Development
3. Beta testing
4. Public release

We'll keep you updated on progress!
```

### Released

```
Your requested feature is now live! 🎉

Feature: [Feature name]
Request: FEAT-12345

What's new:
[Brief description of the feature]

Try it now: https://portkit.cloud/[relevant-page]

Thanks for your feedback - it helped make Portkit better!
```

### Won't Do

```
Update on Feature Request FEAT-12345

Status: Not Planned

After careful consideration, we've decided not to pursue this feature at this time.

Reason:
[Clear, respectful explanation]

We appreciate you taking the time to share your idea. Please continue submitting requests - your feedback helps shape our product!

View our roadmap: https://portkit.cloud/roadmap
```

---

## GitHub Integration

### Public Feature Requests

Features tracked publicly on GitHub:

**Labels:**
- `feature` - Feature request
- `status: submitted` -刚 submitted
- `status: under review` - Being evaluated
- `status: planned` - On roadmap
- `status: in progress` - Being developed
- `status: released` - Live
- `status: wont-do` - Not planned
- `priority: critical/high/medium/low`

### Template

```markdown
## Feature Request

**Category:** [Category]
**Priority:** [Suggested priority]

### Description
[What you want]

### Use Case
[Why you need this]

### Proposed Solution
[How it could work]

### Alternatives Considered
[Any workarounds you've tried]

### Additional Context
[Screenshots, mockups, or links to similar features]

---
**Request ID:** FEAT-12345
**Submitted:** [Date]
**Votes:** [Vote count]
```

---

## Success Metrics

### Submission Metrics

**Weekly:**
- New requests submitted
- Requests by category
- Average votes per request

**Monthly:**
- Total active requests
- Requests implemented
- Average time to decision
- Community engagement (votes, comments)

### Impact Metrics

- Features from user requests implemented per quarter
- User satisfaction with feature request process
- Top contributors (by requests and votes)
- Feature adoption rate after release

---

## Feature Request Guidelines

### Good Feature Requests

✅ **Clear and specific**
- "Add batch conversion for multiple mods at once"

✅ **Explains the problem**
- "I have 20 mods to convert and doing them one by one takes hours"

✅ **Describes the use case**
- "I'm a mod pack creator and need to convert all mods for compatibility"

✅ **Constructive tone**
- "It would be great if..."

### Poor Feature Requests

❌ **Vague**
- "Make it better"

❌ **No context**
- "Add this feature" (without saying what)

❌ **Demanding**
- "You need to add this NOW"

❌ **Duplicate**
- Check existing requests before submitting

---

*Feature Request System Version: 1.0*
*Last Updated: 2026-03-14*
