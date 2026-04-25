# Waitlist Admin Guide

This document covers how to manage and view the Portkit waitlist data.

## Table of Contents

- [Database Connection with pgAdmin](#database-connection-with-pgadmin)
- [Viewing the Waitlist Table](#viewing-the-waitlist-table)
- [API Endpoints](#api-endpoints)
- [Setting Up Daily Cron Job](#setting-up-daily-cron-job)

---

## Database Connection with pgAdmin

### Prerequisites

- pgAdmin installed (download from https://www.pgadmin.org/download/)
- Neon database connection string (from your Neon dashboard)

### Steps to Connect

1. **Get Your Neon Connection String**
   - Log into [Neon Console](https://console.neon.tech/)
   - Select your project → **Dashboard**
   - Go to **Connection Details**
   - Copy the connection string (it looks like: `postgresql://user:password@host.neon.tech/dbname?sslmode=require`)

2. **Add New Server in pgAdmin**
   - Open pgAdmin and right-click **Servers** → **Create** → **Server**
   
3. **Server Configuration**
   - **General Tab**:
     - Name: `Portkit Neon` (or your preferred name)
   
   - **Connection Tab**:
     - Host name: `your-host.neon.tech` (from Neon connection string)
     - Port: `5432` (default)
     - Maintenance database: `neondb` (or your database name)
     - Username: `your-username` (from Neon)
     - Password: `your-password` (from Neon)
     - Check **Save password?**
   
   - **SSL Tab**:
     - SSL mode: `Require`

4. **Connect**
   - Click **Save**
   - Expand the server tree in the sidebar
   - Navigate to: **Servers** → **Portkit Neon** → **Databases** → **your-db** → **Schemas** → **public** → **Tables**

---

## Viewing the Waitlist Table

### Table Structure

The `waitlist_entries` table has the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Unique identifier |
| `email` | VARCHAR(255) | User's email address (unique) |
| `name` | VARCHAR(255) | User's name (optional) |
| `source` | VARCHAR(100) | Signup source (e.g., "landing-page") |
| `created_at` | TIMESTAMP | When the user joined (UTC) |

### Useful Queries

**View all entries (newest first):**
```sql
SELECT * FROM waitlist_entries ORDER BY created_at DESC;
```

**Count total entries:**
```sql
SELECT COUNT(*) FROM waitlist_entries;
```

**Entries added today:**
```sql
SELECT * FROM waitlist_entries 
WHERE created_at >= CURRENT_DATE;
```

**Entries added this week:**
```sql
SELECT * FROM waitlist_entries 
WHERE created_at >= DATE_TRUNC('week', CURRENT_DATE);
```

**Entries by source:**
```sql
SELECT source, COUNT(*) as count 
FROM waitlist_entries 
GROUP BY source 
ORDER BY count DESC;
```

---

## API Endpoints

### Authentication

All waitlist admin endpoints require an `api_key` query parameter. Set the `ADMIN_API_KEY` environment variable in your `.env` file:

```bash
ADMIN_API_KEY=your-secure-random-key
```

### Endpoints

#### 1. Get Waitlist Stats Only

Returns only statistics without full entry details (lighter response).

**Endpoint:** `GET /api/v1/waitlist/stats`

**Parameters:**
- `api_key` (required): Your admin API key

**Example Request:**
```bash
curl "https://your-api-url.com/api/v1/waitlist/stats?api_key=your-secure-random-key"
```

**Example Response:**
```json
{
  "total_count": 150,
  "new_today": 5,
  "new_this_week": 23,
  "source_breakdown": {
    "landing-page": 142,
    "unknown": 8
  }
}
```

#### 2. Get Waitlist Entries

Returns entries with statistics (paginated).

**Endpoint:** `GET /api/v1/waitlist`

**Parameters:**
- `api_key` (required): Your admin API key
- `limit` (optional): Max entries to return (default: 100, max: 1000)
- `offset` (optional): Number of entries to skip (default: 0)

**Example Request:**
```bash
curl "https://your-api-url.com/api/v1/waitlist?api_key=your-secure-random-key&limit=10"
```

**Example Response:**
```json
{
  "total_count": 150,
  "entries": [
    {
      "id": "uuid-here",
      "email": "user@example.com",
      "name": "John",
      "source": "landing-page",
      "created_at": "2026-04-25T10:30:00Z"
    }
  ],
  "new_today": 5,
  "new_this_week": 23
}
```

---

## Setting Up Daily Cron Job

You can set up a daily cron job to fetch waitlist stats and optionally email them.

### Option 1: Simple Shell Script with Cron

1. **Create the script** (`/home/alex/scripts/waitlist-stats.sh`):

```bash
#!/bin/bash

# Configuration
API_URL="https://your-api-url.com/api/v1/waitlist/stats"
API_KEY="your-secure-random-key"
LOG_FILE="/var/log/waitlist-stats.log"

# Fetch stats
response=$(curl -s "${API_URL}?api_key=${API_KEY}")

# Extract values (requires jq)
total=$(echo "$response" | jq -r '.total_count')
new_today=$(echo "$response" | jq -r '.new_today')
new_week=$(echo "$response" | jq -r '.new_this_week')

# Log to file
echo "$(date '+%Y-%m-%d %H:%M:%S') - Total: $total | Today: $new_today | This week: $new_week" >> "$LOG_FILE"

# Optional: Send email (uncomment and configure)
# echo "Waitlist Stats: Total=$total, Today=$new_today, Week=$new_week" | mail -s "Daily Waitlist Update" your@email.com
```

2. **Make it executable:**
```bash
chmod +x /home/alex/scripts/waitlist-stats.sh
```

3. **Add to crontab:**
```bash
crontab -e
```

Add this line for daily at 9 AM:
```
0 9 * * * /home/alex/scripts/waitlist-stats.sh >> /var/log/waitlist-cron.log 2>&1
```

### Option 2: Using n8n (If Running)

If you have n8n running in your infrastructure:

1. Create a new workflow
2. Add **HTTP Request** node:
   - Method: GET
   - URL: `{{$env.API_URL}}/api/v1/waitlist/stats?api_key={{$env.API_KEY}}`
3. Add **Send Email** node or **Slack** node to notify you
4. Set cron schedule (e.g., daily at 9 AM)

### Option 3: GitHub Actions (Alternative)

Create `.github/workflows/waitlist-digest.yml`:

```yaml
name: Daily Waitlist Digest

on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM UTC
  workflow_dispatch:

jobs:
  waitlist-stats:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch waitlist stats
        run: |
          response=$(curl -s "${{ secrets.API_URL }}/api/v1/waitlist/stats?api_key=${{ secrets.ADMIN_API_KEY }}")
          echo "Total: $(echo $response | jq '.total_count')"
          echo "Today: $(echo $response | jq '.new_today')"
          echo "This Week: $(echo $response | jq '.new_this_week')"
      
      - name: Send notification
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          fields: repo,message,commit,author
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## Security Notes

1. **Keep your API key secure** - Never commit it to version control
2. **Use environment variables** - Store in `.env` and reference via environment
3. **Rotate periodically** - Change the key if you suspect it's been compromised
4. **Limit access** - Only give the API key to trusted team members who need waitlist access

---

## Troubleshooting

### "Invalid API key" Error
- Verify `ADMIN_API_KEY` is set in your environment
- Ensure the key matches exactly (no extra spaces or newlines)

### Connection Issues with Neon
- Check your IP is allowlisted in Neon console
- Verify SSL is enabled in connection settings
- Ensure your Neon project is active (not paused)

### Database Table Not Found
- Make sure you're connected to the correct database
- Check that migrations have been run (`alembic upgrade head`)
