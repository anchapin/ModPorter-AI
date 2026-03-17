# Merge Conflict Analysis - GitHub Issue #836

## Summary
15 PRs have merge conflicts requiring rebase due to recent changes to main branch.

## Root Cause
All 15 open PRs target the `main` branch and became stale after **commit 919a5ae** was merged directly to main:

**Commit:** `919a5ae` - "🎨 Palette: Add aria-hidden to icon-only buttons in ConversionHistoryItem (#832)"  
**Date:** March 17, 2026

This commit made critical fixes that conflict with the PR branches:

### Files Modified in Commit 919a5ae:
1. **`ai-engine/tests/test_qa_comprehensive.py`** - Fixed dynamic imports (changed from hardcoded path to relative path)
2. **`ai-engine/tests/test_qa_validator_standalone.py`** - Same fix for dynamic imports
3. **`.github/workflows/ci.yml`** - Multiple CI fixes (Trivy config, pip install, etc.)
4. **`.github/workflows/deploy.yml`** - Trivy configuration updates

### Why Conflicts Occur:
- PR branches were created **before** commit 919a5ae merged to main
- The PR branches contain old versions of these files
- When merging, Git cannot auto-merge because the same lines were modified differently

### Conflicting Files Across All PRs:
- `ai-engine/tests/test_qa_comprehensive.py` (import path change)
- `ai-engine/tests/test_qa_validator_standalone.py` (import path change)
- `frontend/src/components/ConversionProgress/ConversionProgress.tsx` (whitespace)
- `.github/workflows/ci.yml` (CI configuration)

## Solution: Rebase All PRs

The solution is to **rebase** each PR onto the current main branch. This will:
1. Apply PR changes on top of the latest main
2. Include commit 919a5ae's fixes
3. Resolve most conflicts automatically

### Rebase Script

```bash
#!/bin/bash
set -e

# Update main first
git checkout main
git pull origin main

# List of PRs and their branch names
declare -A prs
prs[810]="palette-focus-visible-conversion-history-4003847891242556373"
prs[811]="bolt-optimize-dashboard-stats-calculation-15118324184721153047"
prs[812]="bolt-dashboard-stats-optimization-11104025156848521523"
prs[813]="palette-ux-checkbox-focus-553332443836823931"
prs[814]="sentinel/fix-comparison-api-information-leakage-1535230899631766644"
prs[817]="palette-focus-visible-checkboxes-8030036404827879817"
prs[818]="bolt/optimize-array-filter-length-362091941652466089"
prs[819]="sentinel/fix-info-leakage-http-500-15656402877507307196"
prs[820]="bolt-optimize-array-counts-16792420764399026384"
prs[822]="sentinel/fix-insecure-randomness-13029199472542036102"
prs[823]="bolt-optimize-array-filter-counts-18240854939949337380"
prs[826]="sentinel/fix-insecure-random-id-6069051367449836938"
prs[827]="bolt-status-counts-optimization-17785292945940121830"
prs[828]="palette-a11y-icon-buttons-6636977613006242262"
prs[831]="bolt/optimize-array-statistics-single-pass-11190386349740240137"

# Rebase each PR
for pr in "${!prs[@]}"; do
  branch="${prs[$pr]}"
  echo "Processing PR #$pr -> branch: $branch"
  
  # Fetch and checkout the branch
  git fetch origin "refs/heads/$branch:local_$branch" 2>/dev/null || true
  git checkout "local_$branch"
  
  # Try to rebase onto main
  if git rebase main; then
    echo "Rebase successful for $branch, force pushing..."
    git push --force-with-lease origin "local_$branch:$branch"
  else
    echo "Rebase FAILED for $branch - manual intervention needed"
    git rebase --abort || true
  fi
  
  echo "---"
done

echo "Done processing all PRs"
```

## Prevention
To prevent this issue in the future:
1. **Rebase PRs before merging** instead of using merge commits
2. **Use branch protection rules** to require up-to-date branches before merging
3. **Close and re-create stale PRs** that haven't been updated in X days
4. **Consider using `git rebase main`** instead of `git merge main` when updating branches
