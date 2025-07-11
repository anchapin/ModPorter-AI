#!/bin/bash

# GitHub Repository Security Check Script
# Run this script to verify your repository security configuration

set -e

echo "🔐 GitHub Repository Security Check"
echo "=================================="

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI not found. Please install: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI. Run: gh auth login"
    exit 1
fi

REPO="anchapin/ModPorter-AI"
echo "🔍 Checking repository: $REPO"
echo

# 1. Check repository privacy
echo "1. Repository Privacy"
echo "-------------------"
PRIVACY=$(gh api repos/$REPO --jq '.private')
if [ "$PRIVACY" = "true" ]; then
    echo "✅ Repository is private"
else
    echo "❌ Repository is public - SECURITY RISK with self-hosted runners!"
    echo "   Run: gh repo edit $REPO --visibility private"
fi
echo

# 2. Check workflow permissions
echo "2. Workflow Permissions"
echo "----------------------"
WORKFLOW_PERMS=$(gh api repos/$REPO/actions/permissions/workflow)
DEFAULT_PERMS=$(echo $WORKFLOW_PERMS | jq -r '.default_workflow_permissions')
CAN_APPROVE=$(echo $WORKFLOW_PERMS | jq -r '.can_approve_pull_request_reviews')

if [ "$DEFAULT_PERMS" = "read" ]; then
    echo "✅ Default workflow permissions: read-only"
else
    echo "⚠️  Default workflow permissions: $DEFAULT_PERMS"
    echo "   Consider setting to 'read' for security"
fi

if [ "$CAN_APPROVE" = "false" ]; then
    echo "✅ Workflows cannot approve pull requests"
else
    echo "⚠️  Workflows can approve pull requests"
fi
echo

# 3. Check Actions permissions
echo "3. Actions Permissions"
echo "--------------------"
ACTIONS_PERMS=$(gh api repos/$REPO/actions/permissions)
ENABLED=$(echo $ACTIONS_PERMS | jq -r '.enabled')
ALLOWED=$(echo $ACTIONS_PERMS | jq -r '.allowed_actions')

if [ "$ENABLED" = "true" ]; then
    echo "✅ GitHub Actions enabled"
    echo "   Allowed actions: $ALLOWED"
else
    echo "❌ GitHub Actions disabled"
fi
echo

# 4. Check branch protection
echo "4. Branch Protection (main)"
echo "-------------------------"
BRANCH_PROTECTION=$(gh api repos/$REPO/branches/main/protection 2>/dev/null || echo "null")
if [ "$BRANCH_PROTECTION" != "null" ]; then
    echo "✅ Branch protection enabled for main branch"
    
    # Check specific protections
    REQUIRE_PR=$(echo $BRANCH_PROTECTION | jq -r '.required_pull_request_reviews.required_approving_review_count // 0')
    REQUIRE_STATUS=$(echo $BRANCH_PROTECTION | jq -r '.required_status_checks.strict')
    
    if [ "$REQUIRE_PR" -gt 0 ]; then
        echo "✅ Pull request reviews required ($REQUIRE_PR approvals)"
    else
        echo "⚠️  No pull request reviews required"
    fi
    
    if [ "$REQUIRE_STATUS" = "true" ]; then
        echo "✅ Status checks required"
    else
        echo "⚠️  Status checks not required"
    fi
else
    echo "❌ No branch protection on main branch"
    echo "   Configure at: https://github.com/$REPO/settings/branches"
fi
echo

# 5. Check for self-hosted runners
echo "5. Self-Hosted Runners"
echo "--------------------"
RUNNERS=$(gh api repos/$REPO/actions/runners --jq '.runners[] | select(.labels[].name == "self-hosted")')
if [ -n "$RUNNERS" ]; then
    echo "✅ Self-hosted runners detected"
    echo "   Count: $(echo $RUNNERS | jq -s length)"
    echo "   ⚠️  ENSURE MANUAL APPROVAL IS CONFIGURED FOR FORK PRs"
else
    echo "ℹ️  No self-hosted runners detected"
fi
echo

# 6. Check for secrets
echo "6. Repository Secrets"
echo "-------------------"
SECRETS=$(gh api repos/$REPO/actions/secrets --jq '.total_count')
echo "ℹ️  Total secrets configured: $SECRETS"
if [ "$SECRETS" -gt 0 ]; then
    SECRET_NAMES=$(gh api repos/$REPO/actions/secrets --jq '.secrets[].name' | tr '\n' ' ')
    echo "   Secret names: $SECRET_NAMES"
fi
echo

# 7. Security features check
echo "7. Security Features"
echo "------------------"
SECURITY_ANALYSIS=$(gh api repos/$REPO --jq '{
    secret_scanning: .security_and_analysis.secret_scanning.status,
    dependabot_alerts: .security_and_analysis.dependabot_security_updates.status,
    vulnerability_alerts: .has_vulnerability_alerts
}')

SECRET_SCANNING=$(echo $SECURITY_ANALYSIS | jq -r '.secret_scanning')
DEPENDABOT=$(echo $SECURITY_ANALYSIS | jq -r '.dependabot_alerts')
VULN_ALERTS=$(echo $SECURITY_ANALYSIS | jq -r '.vulnerability_alerts')

if [ "$SECRET_SCANNING" = "enabled" ]; then
    echo "✅ Secret scanning enabled"
else
    echo "⚠️  Secret scanning: $SECRET_SCANNING"
fi

if [ "$DEPENDABOT" = "enabled" ]; then
    echo "✅ Dependabot security updates enabled"
else
    echo "⚠️  Dependabot security updates: $DEPENDABOT"
fi

if [ "$VULN_ALERTS" = "true" ]; then
    echo "✅ Vulnerability alerts enabled"
else
    echo "⚠️  Vulnerability alerts disabled"
fi
echo

# Summary
echo "📋 Summary"
echo "========="
echo "✅ = Configured securely"
echo "⚠️  = Needs attention"
echo "❌ = Security risk"
echo
echo "🔗 Manual configuration required at:"
echo "   Actions settings: https://github.com/$REPO/settings/actions"
echo "   Branch protection: https://github.com/$REPO/settings/branches"
echo "   Security settings: https://github.com/$REPO/settings/security"
echo
echo "📖 See .github/security-config-guide.md for detailed instructions"