# Beta Invite Email Template

**Purpose:** Welcome accepted beta testers and provide onboarding information
**Trigger:** Manual send after application acceptance

---

## Email 1: Welcome / Acceptance

**Subject:** Welcome to Portkit Beta! 🎮

**Body:**

Hi {{name}},

Congratulations! You've been accepted into the Portkit Beta Program.

**Your Beta Access:**
- Email: {{user_email}}
- Temp Password: {{temp_password}}
- Login: portkit.ai/login

**Getting Started:**
1. Log in at portkit.ai/login
2. Upload your first Java mod (.jar file)
3. Let our AI convert it to Bedrock format
4. Download your .mcaddon file

**Beta Period:** 8 weeks from today
**Your Tier:** Creator (free during beta)

**Need Help?**
- 📚 Docs: docs.portkit.ai
- 💬 Discord: https://discord.gg/portkit (use invite code: {{discord_invite_code}})
- 🐛 Bug Reports: #beta-bugs channel on Discord
- 📧 Email: beta@portkit.cloud

**What Converts Well in Beta:**
- Items, blocks, armor, tools: 80%+ automated
- Basic entities: 60-80% automated
- Recipes, loot tables: 80%+ automated

**Known Limitations:**
- Custom rendering: Requires manual work
- Network packet handlers: Not supported in beta

**Expected Time Investment:**
We ask for 2-4 hours/week of testing and feedback during the beta period. This helps us improve the product before launch.

**We'd Love to Hear About:**
- Which mods you're trying to convert
- What worked well
- What didn't work as expected
- Features you'd like to see

**Looking Forward:**
We're excited to have you on board. Your feedback will directly shape how Portkit evolves.

Happy modding!

The Portkit Team

---

## Email 2: Week 1 Check-in

**Subject:** Portkit Beta Week 1 - How's It Going?

**Body:**

Hi {{name}},

It's been about a week since you joined the Portkit Beta. How's it going?

**Quick Status Check:**
- Have you been able to log in and try a conversion?
- Did you encounter any issues?
- Any early feedback to share?

**If You Haven't Started Yet:**
No worries! Here's a quick start guide:
1. Go to portkit.ai
2. Upload any .jar file from your mod
3. Click "Convert" and wait a few minutes
4. Download the result

**Resources:**
- Quickstart Guide: docs.portkit.ai/quickstart
- Video Tutorial: youtube.com/@portkit (coming soon)
- Discord #beta-support: https://discord.gg/portkit

**This Week's Focus:**
We're particularly testing conversion quality for items and blocks right now. If you have mods with these features, those would be great to test first.

Reply to this email or post in Discord if you have any questions!

Best,
The Portkit Team

---

## Email 3: Feedback Request (Week 2)

**Subject:** Share Your Portkit Feedback - 2 Minutes = Big Impact

**Body:**

Hi {{name}},

Quick pulse check! Your feedback is making Portkit better for everyone.

**One quick question:**
What's the #1 thing you'd like to see improved in Portkit?

Reply with just a sentence or two - we read every response.

**Or take our 2-minute survey:**
[survey link]

**Recent Updates Based on Beta Feedback:**
- Fixed issue with texture paths not resolving
- Added support for named entity types
- Improved recipe conversion for furnace recipes

Thanks for being part of this!
{{dev_name}}
Portkit Development Team

---

## Email 4: Bug Report Follow-up

**Subject:** Portkit - Status Update on Your Bug Report

**Body:**

Hi {{name}},

Thank you for your bug report in #beta-bugs on {{date_reported}}.

**Status Update:**
- Bug ID: #{{bug_id}}
- Category: {{bug_category}}
- Status: {{status}} (Under Review / Fixed / Known Limitation)

**Next Steps:**
{{next_steps}}

If you have additional details that might help, reply to this email or reply in the Discord thread.

Thanks again for helping us improve Portkit!

Best,
{{dev_name}}

---

## Email 5: Beta Conclusion / Launch Prep

**Subject:** Portkit Beta Ending Soon - Your Path Forward

**Body:**

Hi {{name}},

The Portkit Beta Program is wrapping up. Thank you for being part of this!

**Your Beta Stats:**
- Conversions completed: {{conversion_count}}
- Feedback submitted: {{feedback_count}}
- Bugs reported: {{bugs_reported}}

**What's Next:**
Beta ends on {{beta_end_date}}. Your feedback has been invaluable.

**Launch Offer for Beta Testers:**
As a thank you, we're offering 50% off the Creator tier for 6 months when we launch. Code: {{launch_code}}

**Stay Connected:**
- Discord: https://discord.gg/portkit (you're welcome to stay!)
- Twitter: @portkit
- Newsletter: portkit.ai/newsletter

**Launch Date:** {{launch_date}}

Would you be willing to provide a testimonial or case study about your experience? Reply yes/no - it's completely optional but helps other modders discover Portkit.

It's been a pleasure working with you.

All the best,
The Portkit Team

---

## Email Variables Reference

| Variable | Description |
|----------|-------------|
| `{{name}}` | User's display name |
| `{{user_email}}` | User's email address |
| `{{temp_password}}` | Temporary password for new accounts |
| `{{discord_invite_code}}` | Discord invite code |
| `{{dev_name}}` | Developer name handling the case |
| `{{date_reported}}` | Date bug was reported |
| `{{bug_id}}` | Internal bug tracking ID |
| `{{bug_category}}` | Category of the bug |
| `{{status}}` | Current bug status |
| `{{next_steps}}` | What comes next for this bug |
| `{{conversion_count}}` | Number of conversions user did |
| `{{feedback_count}}` | Number of feedback submissions |
| `{{bugs_reported}}` | Number of bugs reported |
| `{{beta_end_date}}` | End date of beta period |
| `{{launch_code}}` | Discount code for launch |
| `{{launch_date}}` | Public launch date |

---

*Document Version: 1.0*
*Created: 2026-05-02*
