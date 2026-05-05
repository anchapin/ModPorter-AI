# Beta Discord Channels Setup

**Purpose:** Set up #beta-general, #beta-bugs, and #beta-feedback channels for beta testers
**Related:** docs/DISCORD-SETUP.md (existing server setup)

---

## Beta Channels Overview

| Channel | Purpose | Permissions |
|---------|---------|-------------|
| #beta-general | General discussion for beta testers | Beta Tester role only |
| #beta-bugs | Bug reports and issue tracking | Beta Tester role only |
| #beta-feedback | Feature feedback and suggestions | Beta Tester role only |

---

## Channel Setup Instructions

### Via Discord UI

1. **Open Discord** and navigate to the Portkit server
2. **Create a new category** (optional, for organization):
   - Right-click server → "Create Category"
   - Name: "BETA TESTERS" or similar
3. **Create each channel:**
   - Click "+" next to category
   - Channel type: Text Channel
   - Add the following channels:
     - `beta-general` - General beta discussion
     - `beta-bugs` - Bug report submissions
     - `beta-feedback` - Feature suggestions and feedback

### Via Discord API / Bot Commands

```discord
#create beta-general
#create beta-bugs
#create beta-feedback

#set #beta-general topic "General discussion for beta testers. Read rules before posting."
#set #beta-bugs topic "Report bugs here. Use the template: https://portkit.ai/bug-template"
#set #beta-feedback topic "Share feature suggestions and product feedback."
```

---

## Channel Permissions

### Beta Tester Role Permissions (for each beta channel)

| Permission | Status |
|------------|--------|
| View Channel | ✅ Allowed |
| Send Messages | ✅ Allowed |
| Embed Links | ✅ Allowed |
| Attach Files | ✅ Allowed |
| Add Reactions | ✅ Allowed |
| Use Threads | ✅ Allowed |
| Create Public Threads | ❌ Disallowed |
| Create Private Threads | ✅ Allowed |
| Manage Threads | ❌ Disallowed |
| Manage Messages | ❌ Disallowed |
| Pin Messages | ❌ Disallowed |

### Default Role (@everyone)

| Permission | Status |
|------------|--------|
| View Channel | ❌ Disallowed (unless public) |
| Send Messages | ❌ Disallowed |

---

## Channel Topics / Descriptions

### #beta-general
```
Welcome to the beta general channel!

This is a space for beta testers to:
- Discuss their conversion experiences
- Ask questions about the beta program
- Share tips and tricks
- Connect with other beta testers

Guidelines:
- Be respectful to other testers
- Don't share beta features publicly (confidentiality)
- Search before asking common questions

Beta Timeline: 8 weeks
Your tier: Creator (free during beta)
```

### #beta-bugs
```
Bug Report Guidelines:

Before submitting a bug:
1. Search if it's already reported
2. Check known limitations (custom rendering, network packets)

Bug Report Template:
```
## Bug Report
**Mod used:** [mod name]
**Conversion type:** [items/entities/recipes]
**Date:** [YYYY-MM-DD]
**Description:** [what happened]
**Expected:** [what should happen]
**Actual:** [what actually happened]
**Logs:** [attach conversion logs]
```

Response time: < 24 hours
For critical bugs, DM @developer directly.
```

### #beta-feedback
```
Feature Feedback & Suggestions

We want to hear what you think!

What to share:
- Features you'd like to see
- UX improvements
- Conversion quality feedback
- Third-party tool integrations

Feedback is reviewed weekly by the dev team.

Top suggestions get优先 consideration for the roadmap.
(Your feedback shapes Portkit's future!)
```

---

## Welcome Message for Each Channel

### #beta-general Welcome
```
👋 Welcome to #beta-general!

This is your space to connect with other beta testers.

**What you can do here:**
- Ask general questions about the beta
- Share your conversion experiences
- Discuss modding topics with fellow creators
- Get help with common issues

**Beta Program Info:**
- Timeline: 8 weeks
- Your tier: Creator (free access)
- Discord: https://discord.gg/portkit

Happy testing! 🎮
```

### #beta-bugs Welcome
```
🐛 Welcome to #beta-bugs!

This channel is for reporting bugs and issues you encounter during conversion.

**Before posting:**
- Check if the bug is already reported
- Review known limitations (custom rendering, network packets)
- Gather your conversion logs

**Bug Report Template:**
```
## Bug Report
**Mod used:** [mod name]
**Conversion type:** [items/entities/recipes]
**Date:** [YYYY-MM-DD]
**Description:** [what happened]
**Expected:** [what should happen]
**Actual:** [what actually happened]
**Logs:** [attach conversion logs]
```

Response time: < 24 hours
```

### #beta-feedback Welcome
```
💡 Welcome to #beta-feedback!

Your feedback shapes Portkit's future!

**What to share:**
- Features you'd like to see
- UX improvements and suggestions
- Conversion quality feedback
- Integration ideas

**What converts well (beta):**
- Items, blocks, armor, tools: 80%+ automated
- Basic entities: 60-80% automated
- Recipes, loot tables: 80%+ automated

We read every piece of feedback.
Top suggestions get priority on our roadmap.
```

---

## Pin Messages

### #beta-general Pinned
- Link to beta guidelines
- Link to getting started guide
- Discord server invite (if needed)

### #beta-bugs Pinned
- Bug report template
- Known limitations list
- Support contact info

### #beta-feedback Pinned
- Feedback submission guidelines
- What's on our roadmap
- Success stories (when available)

---

## Integration with Existing Server

Add these channels to the existing server structure documented in `docs/DISCORD-SETUP.md`:

```
🔧 BETA-TESTERS ONLY (existing)
├── #beta-feedback          ← already exists
├── #preview-features       ← already exists
└── #direct-dev-access      ← already exists

🆕 BETA-SPECIFIC (new)
├── #beta-general           ← NEW
├── #beta-bugs              ← NEW
└── #beta-feedback          ← already exists, update topic
```

---

## Optional: Bot Commands for Beta Channels

### Auto-response for #beta-bugs

```
#set #beta-bugs slowmode 60  (1 message per minute to prevent spam)
```

### Notification for New Beta Testers

```
#welcome #beta-general
#welcome #beta-bugs
#welcome #beta-feedback
```

---

*Document Version: 1.0*
*Created: 2026-05-05*
*Related Issue: #1166*