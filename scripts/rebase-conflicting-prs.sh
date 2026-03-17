#!/bin/bash
# Script to automate rebasing PRs with CI workflow conflicts
# This script resolves the issue where 15 PRs have merge conflicts due to CI workflow updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# List of PRs affected by CI workflow conflicts
AFFECTED_PRS=(
    # Sentinel (Security) PRs
    "826"
    "822"
    "819"
    "814"
    # Bolt (Optimization) PRs
    "831"
    "827"
    "823"
    "820"
    "818"
    "812"
    "811"
    # Palette (Accessibility) PRs
    "828"
    "817"
    "813"
    "810"
)

echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}CI Workflow Conflict Resolution Script${NC}"
echo -e "${YELLOW}======================================${NC}"
echo ""
echo "This script will rebase affected PRs to resolve CI workflow conflicts."
echo "The CI workflow conflicts are non-functional (formatting/optimization changes)."
echo ""

# Function to rebase a single PR
rebase_pr() {
    local pr_number=$1
    local pr_branch=""
    
    echo -e "${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}Processing PR #${pr_number}${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    
    # Get the PR branch name using gh
    pr_branch=$(gh pr view "$pr_number" --json headRefName --jq '.headRefName' 2>/dev/null) || {
        echo -e "${RED}Failed to get branch name for PR #${pr_number}${NC}"
        return 1
    }
    
    echo "PR #${pr_number} branch: ${pr_branch}"
    
    # Check if branch exists locally
    if ! git rev-parse --verify "${pr_branch}" >/dev/null 2>&1; then
        echo "Fetching and checking out PR branch..."
        gh pr checkout "$pr_number" --force || {
            echo -e "${RED}Failed to checkout PR #${pr_number}${NC}"
            return 1
        }
    else
        echo "Checking out existing branch..."
        git checkout "${pr_branch}" || {
            echo -e "${RED}Failed to checkout branch ${pr_branch}${NC}"
            return 1
        }
    fi
    
    # Fetch latest main
    echo "Fetching latest main branch..."
    git fetch origin main || git fetch origin main:main
    
    # Attempt rebase
    echo "Rebasing on main..."
    if git rebase origin/main; then
        echo -e "${GREEN}Rebase successful!${NC}"
        
        # Push force
        echo "Force pushing..."
        git push --force-with-lease origin "${pr_branch}" || {
            echo -e "${RED}Failed to push${NC}"
            return 1
        }
        
        echo -e "${GREEN}✓ PR #${pr_number} rebased successfully${NC}"
    else
        echo -e "${YELLOW}Rebase has conflicts - resolving automatically${NC}"
        
        # For CI workflow conflicts, we take the main branch version
        if [ -f ".github/workflows/ci.yml" ]; then
            echo "Resolving CI workflow conflicts (using main branch version)..."
            git checkout --theirs ".github/workflows/ci.yml"
            git add ".github/workflows/ci.yml"
        fi
        
        # Check if there are other conflicts
        if git diff --name-only --diff-filter=U | grep -q .; then
            echo -e "${YELLOW}Other conflicts detected, skipping this PR${NC}"
            git rebase --abort
            echo -e "${RED}✗ PR #${pr_number} has unresolved conflicts${NC}"
            return 1
        fi
        
        # Continue rebase
        git rebase --continue
        
        # Push force
        echo "Force pushing..."
        git push --force-with-lease origin "${pr_branch}" || {
            echo -e "${RED}Failed to push${NC}"
            return 1
        }
        
        echo -e "${GREEN}✓ PR #${pr_number} rebased and conflicts resolved${NC}"
    fi
    
    return 0
}

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Authenticate with GitHub
echo "Checking GitHub authentication..."
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: Not authenticated with GitHub${NC}"
    echo "Please run: gh auth login"
    exit 1
fi

# Count successes and failures
success_count=0
failure_count=0

# Process each PR
for pr in "${AFFECTED_PRS[@]}"; do
    if rebase_pr "$pr"; then
        ((success_count++))
    else
        ((failure_count++))
    fi
    echo ""
done

# Summary
echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}Summary${NC}"
echo -e "${YELLOW}======================================${NC}"
echo -e "Successful: ${GREEN}${success_count}${NC}"
echo -e "Failed: ${RED}${failure_count}${NC}"
echo ""

if [ $failure_count -gt 0 ]; then
    echo -e "${YELLOW}Some PRs require manual intervention.${NC}"
    exit 1
else
    echo -e "${GREEN}All PRs have been rebased successfully!${NC}"
    exit 0
fi
