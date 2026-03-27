# GitHub Project Board Setup Guide

This guide explains how to set up a GitHub Project (v2) board for ModPorter-AI with proper columns, labels, and automation.

## Overview

GitHub Projects (v2) is a flexible project management tool that integrates with issues and pull requests. This setup provides a Kanban-style workflow for tracking work on the ModPorter-AI project.

## Step 1: Create a New GitHub Project

1. Navigate to the [GitHub Projects page](https://github.com/orgs/anchapin/projects) or go to the repository's Projects tab
2. Click "New Project"
3. Select "New project" (not "New project (classic)")
4. Name the project: **ModPorter-AI Development**
5. Choose "Board" as the template (this gives us a Kanban-style layout)
6. Click "Create"

## Step 2: Set Up Kanban Columns

The default board comes with three columns. Modify them to match this workflow:

| Column | Description |
|--------|-------------|
| **Backlog** | Issues that need to be triaged or are not yet ready for work |
| **Ready** | Issues that are well-defined and ready to be picked up |
| **In Progress** | Issues currently being worked on |
| **Review** | Issues with open PRs or needing review |
| **Done** | Completed issues (closed) |

### How to Add/Edit Columns:

1. Click the "+" button next to the last column to add a new column
2. Click the "..." menu on a column to rename or delete it
3. Drag columns to reorder them

## Step 3: Configure Status Field

The Status field is the main field for tracking issue progress. Configure it with these options:

1. Click on the "..." menu in the project header
2. Select "Settings"
3. Under "Fields", find the "Status" field
4. Ensure the options match your column names:
   - Backlog
   - Ready
   - In Progress
   - Review
   - Done

## Step 4: Add Custom Fields

Add these custom fields to enhance project tracking:

### Priority Field
- Type: Single select
- Options:
  - `priority-1` (Critical)
  - `priority-2` (High)
  - `priority-3` (Medium)
  - `priority-4` (Low)

### Size Field
- Type: Single select
- Options:
  - `XS` (Extra Small - < 1 hour)
  - `S` (Small - 1-2 hours)
  - `M` (Medium - half day)
  - `L` (Large - full day)
  - `XL` (Extra Large - multiple days)

### Milestone Field
- Type: Iteration (sprints) or single select
- Configure based on project milestones

### Category Field
- Type: Single select
- Options:
  - `bug`
  - `feature`
  - `documentation`
  - `testing`
  - `infrastructure`
  - `refactor`

## Step 5: Add Issues to the Project

### Option A: Add All Open Issues via GitHub CLI

```bash
# List all open issues and add them to the project
gh issue list --repo anchapin/ModPorter-AI --state open --limit 1000 --json number,title,labels | \
  jq -r '.[] | .number' | \
  while read issue; do
    gh project item-add <PROJECT_NUMBER> --owner anchapin --url "https://github.com/anchapin/ModPorter-AI/issues/$issue"
  done
```

### Option B: Add Issues Manually

1. Go to the Issues page of the repository
2. Select issues using the checkboxes
3. Click "Projects" in the sidebar
4. Select the project to add them to

### Option C: Bulk Add via Project View

1. Open the project
2. Click "Add item" 
3. Paste issue URLs or search for issues

## Step 6: Configure Automation Rules

GitHub Projects (v2) supports built-in automations. Configure these:

### Built-in Automations

1. Open the project settings
2. Navigate to "Workflows" (or "Automations")
3. Enable these default workflows:

| Workflow | Description |
|----------|-------------|
| **Item added to project** | Set Status to "Backlog" when a new item is added |
| **Item reopened** | Set Status to "In Progress" when an issue is reopened |
| **Item closed** | Set Status to "Done" when an issue is closed |
| **Pull request merged** | Set Status to "Done" when a PR is merged |

### Custom Automation with GitHub Actions

Create `.github/workflows/project-automation.yml`:

```yaml
name: Project Board Automation

on:
  issues:
    types: [opened, closed, reopened, assigned, labeled]
  pull_request:
    types: [opened, closed, review_requested, approved]

jobs:
  automate-project-card:
    runs-on: ubuntu-latest
    steps:
      - name: Move to In Progress on Assignment
        if: github.event.action == 'assigned'
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.PROJECT_TOKEN }}
          script: |
            // Add logic to move issue to "In Progress" column
            console.log('Issue assigned:', context.payload.issue.number);
      
      - name: Move to Review on PR Opened
        if: github.event_name == 'pull_request' && github.event.action == 'opened'
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.PROJECT_TOKEN }}
          script: |
            // Add logic to move linked issue to "Review" column
            console.log('PR opened:', context.payload.pull_request.number);
```

## Step 7: Set Up Views

Create different views for different purposes:

### Default Board View
- Group by: Status
- Sort by: Priority

### Active Work View
- Filter: `status:"In Progress" OR status:"Review"`
- Sort by: Updated at (descending)

### Backlog View
- Filter: `status:"Backlog" OR status:"Ready"`
- Sort by: Priority

### By Priority View
- Group by: Priority
- Sort by: Status

### By Milestone View
- Group by: Milestone
- Sort by: Status

## Step 8: Configure Labels

Ensure the repository has consistent labels:

| Label | Color | Description |
|-------|-------|-------------|
| `bug` | #d73a4a | Something isn't working |
| `documentation` | #0075ca | Improvements or additions to documentation |
| `enhancement` | #a2eeef | New feature or request |
| `good-first-issue` | #7057ff | Good for newcomers |
| `help-wanted` | #008672 | Extra attention is needed |
| `priority-1` | #b60205 | Critical - must be fixed immediately |
| `priority-2` | #d93f0b | High - should be fixed soon |
| `priority-3` | #fbca04 | Medium - normal priority |
| `priority-4` | #0e8a16 | Low - nice to have |
| `blocked` | #000000 | Blocked by external dependency |
| `wontfix` | #ffffff | Will not be worked on |

## Step 9: Link Project to Repository

1. Go to repository Settings
2. Navigate to "Features" section
3. Ensure "Projects" is enabled
4. The project should now appear in the repository's Projects tab

## Step 10: Add Milestone Tracking

### Create Milestones

1. Go to Issues → Milestones
2. Create milestones for major releases:
   - MVP Release
   - v1.0.0
   - v1.1.0
   - etc.

### Link Issues to Milestones

When creating or editing issues, assign them to appropriate milestones.

### Track Progress

Use the "By Milestone" view to see progress toward each milestone.

## CLI Commands Reference

### Project Management

```bash
# List projects
gh project list --owner anchapin

# View project details
gh project view <PROJECT_NUMBER> --owner anchapin

# Create a new project
gh project create --owner anchapin --title "Project Name"

# Add item to project
gh project item-add <PROJECT_NUMBER> --owner anchapin --url <ISSUE_URL>

# List project items
gh project item-list <PROJECT_NUMBER> --owner anchapin

# Update item status
gh project item-edit --project-id <PROJECT_ID> --id <ITEM_ID> --field-id <STATUS_FIELD_ID> --single-select-option-id <OPTION_ID>
```

### Issue Management

```bash
# List open issues
gh issue list --repo anchapin/ModPorter-AI --state open

# Create issue with labels and project
gh issue create --repo anchapin/ModPorter-AI --title "Title" --body "Description" --label "bug,priority-2" --project "ModPorter-AI Development"

# Add issue to project
gh issue edit <ISSUE_NUMBER> --repo anchapin/ModPorter-AI --add-project "ModPorter-AI Development"
```

## Best Practices

1. **Keep issues atomic**: One issue should represent one unit of work
2. **Use templates**: Create issue templates for consistent formatting
3. **Regular triage**: Review the Backlog weekly to move items to Ready
4. **Update status**: Always move issues to the correct column as work progresses
5. **Link PRs**: Reference issues in PRs using "Fixes #123" or "Closes #123"
6. **Use labels consistently**: Labels help with filtering and prioritization
7. **Set milestones**: Assign issues to milestones for release planning

## Troubleshooting

### Issue not appearing in project
- Check if the issue is open
- Verify the project is linked to the repository
- Try adding the issue manually

### Automation not working
- Verify the GitHub Actions workflow is enabled
- Check if the `PROJECT_TOKEN` secret is set correctly
- Ensure the token has `project` scope

### Cannot edit project fields
- Verify you have write access to the repository
- Check if the project is owned by the same account/organization

## Resources

- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub CLI Projects Commands](https://cli.github.com/manual/gh_project)
- [GitHub Actions for Project Automation](https://github.com/actions/github-script)