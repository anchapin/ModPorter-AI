# ModPorter-AI Community Discord Server Setup

## Server Information

- **Server Name**: ModPorter-AI Community
- **Server Description**: Official community server for ModPorter-AI - AI-powered Minecraft Java to Bedrock conversion tool
- **Invite Link**: [Create via Discord Developer Portal](https://discord.com/developers/applications)

---

## Channel Structure

### Required Channels (5+)

| Channel Name | Category | Description | Permissions |
|--------------|----------|-------------|-------------|
| `#announcements` | Information | Launch updates, feature releases, important news | @everyone read-only |
| `#general` | Community | General discussion, introductions | @everyone |
| `#support` | Support | Technical help, troubleshooting | @everyone |
| `#feedback` | Feedback | User suggestions, feature requests | @everyone |
| `#showcase` | Community | Converted mod showcases, screenshots | @everyone |

### Optional Channels

| Channel Name | Category | Description |
|--------------|----------|-------------|
| `#dev-talk` | Development | Technical discussions, API development |
| `#off-topic` | Community | Non-Minecraft discussions |
| `#beta-testing` | Beta Program | Beta tester coordination |

---

## Role Configuration

### Required Roles

| Role Name | Color | Permissions | Members |
|-----------|-------|-------------|---------|
| @Admin | Red | Full server access | Core team |
| @Moderator | Blue | Manage channels, messages, users | Community managers |
| @Beta Tester | Green | Access to beta channels | Beta participants |
| @Member | Default | Basic access | General members |

### Role Hierarchy

1. @Admin (top)
2. @Moderator
3. @Beta Tester
4. @Member
5. @everyone

---

## Bot Configuration

### Required Bot Permissions

```
- Manage Channels
- Manage Roles
- Manage Messages
- Send Messages
- Embed Links
- Read Message History
- Use Slash Commands
```

### Bot Commands (Optional)

```python
# Example slash commands to implement
/ping - Bot latency check
/stats - Conversion statistics
/help - Help information
/feedback - Submit feedback directly
```

---

## Webhook Setup

### Alert Webhook

Create a webhook in `#announcements` for:
- New feature releases
- Important updates
- Server status changes

### Support Webhook (Internal)

Create a webhook for internal notifications when:
- New support tickets submitted
- Critical errors detected
- User feedback received

---

## Moderation Guidelines

### Community Rules

1. **Be Respectful** - Treat all members with respect
2. **Stay on Topic** - Keep discussions relevant to channels
3. **No Spam** - No excessive self-promotion or spam
4. **Follow Discord ToS** - Adhere to Discord's terms of service

### Moderator Commands

```
- /warn [user] [reason] - Warn a member
- /kick [user] [reason] - Kick a member
- /ban [user] [reason] - Ban a member
- /slowmode [seconds] - Set slowmode
```

---

## Setup Instructions (Manual)

### Step 1: Create Server
1. Go to Discord Developer Portal
2. Click "New Application"
3. Name it "ModPorter-AI"
4. Click "Create"
5. Go to "OAuth2" > "URL Generator"
6. Select "bot" scope
7. Select required permissions
8. Copy generated URL and open in browser

### Step 2: Configure Channels
1. Create categories first
2. Create channels within categories
3. Set channel permissions

### Step 3: Set Up Roles
1. Create roles in hierarchy order
2. Assign permissions to roles
3. Configure role colors

### Step 4: Add Bot
1. Go to "Bot" in Developer Portal
2. Click "Reset Token" if needed
3. Copy token for bot configuration
4. Add bot to server using OAuth2 URL

---

## Integration with ModPorter-AI

### Error Alerting Integration

To integrate with error alerting system:

1. Create a webhook in Discord
2. Add webhook URL to backend config:
```bash
# In .env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Feedback Integration

To send user feedback to Discord:

1. Create a webhook in `#feedback` channel
2. Configure in backend settings

---

## Maintenance

### Weekly Tasks
- Review #feedback for new suggestions
- Check #support for unresolved issues
- Update announcements with new features

### Monthly Tasks
- Clean up inactive members
- Review and update roles
- Analyze community growth metrics

---

## Contact

For issues with server setup, contact the development team.

---

*Last updated: 2026-03-18*
