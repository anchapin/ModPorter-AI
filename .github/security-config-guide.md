# GitHub Repository Security Configuration for Self-Hosted Runners

⚠️ **CRITICAL**: This configuration is essential to prevent malicious code execution on your self-hosted runner.

## Automated Configuration (Completed)

✅ **Repository made private** - This is the most important security measure
✅ **Workflow permissions set to read-only** - Limits token permissions
✅ **Pull request reviews cannot be approved by workflows** - Prevents automated approvals

## Manual Configuration Required

The following settings must be configured manually through the GitHub web interface:

### 1. Actions General Settings

Navigate to: **Settings** → **Actions** → **General**

#### Configure these settings:

**Actions permissions:**
- ✅ Allow all actions and reusable workflows

**Artifact and log retention:**
- Set to 90 days (or your preferred duration)

**Fork pull request workflows from outside collaborators:**
- ⚠️ **CRITICAL**: Select **"Require approval for first-time contributors who are new to GitHub"**
- This ensures malicious users can't immediately run workflows

**Fork pull request workflows in private repositories:**
- ⚠️ **CRITICAL**: Select **"Require approval for all outside collaborators"**
- This means ALL external contributors need approval before running workflows

### 2. Branch Protection Rules

Navigate to: **Settings** → **Branches**

#### Create rule for `main` branch:
- **Require a pull request before merging**: ✅
- **Require approvals**: ✅ (minimum 1)
- **Dismiss stale reviews**: ✅
- **Require review from CODEOWNERS**: ✅ (if you have CODEOWNERS)
- **Require status checks to pass**: ✅
- **Require branches to be up to date**: ✅
- **Require conversation resolution**: ✅
- **Restrict pushes that create files**: ✅

### 3. Additional Security Settings

Navigate to: **Settings** → **Security**

#### Secret scanning:
- **Secret scanning**: ✅ Enable
- **Push protection**: ✅ Enable

#### Vulnerability alerts:
- **Dependabot alerts**: ✅ Enable
- **Dependabot security updates**: ✅ Enable

## Verification Commands

Run these commands to verify your configuration:

```bash
# Check repository privacy
gh repo view --json private

# Check workflow permissions
gh api repos/anchapin/ModPorter-AI/actions/permissions/workflow

# Check branch protection
gh api repos/anchapin/ModPorter-AI/branches/main/protection
```

## Self-Hosted Runner Security

### Runner Configuration
```bash
# When setting up your runner, use a dedicated user account
sudo useradd -m github-runner
sudo -u github-runner ./config.sh --url https://github.com/anchapin/ModPorter-AI --token YOUR_TOKEN

# Use labels for isolation
# Labels: self-hosted, ollama, local-dev
```

### Environment Isolation
```bash
# Consider running in a container or VM
docker run -it --name github-runner \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/actions-runner:/home/github-runner/actions-runner \
  ubuntu:22.04
```

## PR Review Process

### For External Contributors:

1. **Review the code changes** in the PR
2. **Check for suspicious patterns**:
   - Unauthorized file access
   - Network calls to external services
   - Modification of CI/CD files
   - Addition of executable files
3. **Manually approve the workflow** if safe
4. **Monitor the workflow execution**

### Red Flags to Watch For:

⚠️ **Dangerous patterns in PRs:**
- Changes to `.github/workflows/` files
- New scripts with network access
- Modifications to `requirements.txt` or `package.json`
- Addition of binary files
- Obfuscated code
- External API calls
- File system access outside project directory

## Emergency Procedures

### If Malicious Code is Detected:

1. **Immediately stop the runner**:
   ```bash
   sudo ./svc.sh stop
   ```

2. **Review runner logs**:
   ```bash
   sudo journalctl -u actions.runner.anchapin-ModPorter-AI.YOUR_RUNNER_NAME
   ```

3. **Check for unauthorized changes**:
   ```bash
   # Check for new files
   find /home/github-runner -type f -newer /home/github-runner/actions-runner/config.sh
   
   # Check network connections
   sudo netstat -tulpn | grep ESTABLISHED
   ```

4. **Clean and restart**:
   ```bash
   # Remove and reconfigure runner
   ./config.sh remove
   ./config.sh --url https://github.com/anchapin/ModPorter-AI --token NEW_TOKEN
   sudo ./svc.sh start
   ```

## Monitoring

### Set up alerts for:
- New workflow runs from external contributors
- Failed workflow runs
- Unusual resource usage
- Network activity during workflow runs

### Log monitoring:
```bash
# Monitor runner logs
tail -f /home/github-runner/actions-runner/_diag/Runner_*.log

# Monitor system resources
htop
iotop
```

## Best Practices

1. **Regular Updates**: Keep runner software updated
2. **Minimal Permissions**: Run runner with minimal required permissions
3. **Network Isolation**: Consider firewall rules to limit runner network access
4. **Backup Strategy**: Regular backups of runner configuration
5. **Incident Response Plan**: Have a plan for handling security incidents

## Repository Access Control

### Collaborator Management:
- Only add trusted collaborators
- Use teams for organization
- Regularly audit access permissions
- Remove inactive collaborators

### Token Management:
- Use fine-grained personal access tokens
- Rotate tokens regularly
- Monitor token usage
- Revoke compromised tokens immediately

This configuration provides defense in depth against malicious code execution while maintaining the benefits of automated testing with your self-hosted runner.