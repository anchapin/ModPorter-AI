# Self-Hosted GitHub Actions Runner Setup

This guide explains how to set up a self-hosted GitHub Actions runner to run integration tests with Ollama locally.

## Prerequisites

1. **Ollama installed and running**
   ```bash
   # Install Ollama (if not already installed)
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Start Ollama service
   ollama serve
   
   # Pull the required model
   ollama pull llama3.2
   ```

2. **Python 3.11+ installed**
   ```bash
   python --version  # Should show 3.11 or higher
   ```

3. **Git installed**
   ```bash
   git --version
   ```

## Setting Up the Self-Hosted Runner

### 1. Navigate to GitHub Repository Settings

1. Go to your GitHub repository
2. Click on **Settings** tab
3. Go to **Actions** → **Runners**
4. Click **New self-hosted runner**

### 2. Download and Configure Runner

Follow GitHub's instructions to download the runner for your OS:

**For Linux:**
```bash
# Create a folder for the runner
mkdir actions-runner && cd actions-runner

# Download the latest runner package
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Extract the installer
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz
```

### 3. Configure the Runner

```bash
# Create the runner and start the configuration experience
./config.sh --url https://github.com/YOUR_USERNAME/ModPorter-AI --token YOUR_TOKEN

# When prompted for labels, add: ollama
# This matches the [self-hosted, ollama] label in the workflow
```

**Important Configuration Options:**
- **Runner group**: Default
- **Runner name**: Choose a descriptive name (e.g., `local-ollama-runner`)
- **Labels**: Add `ollama` (this is crucial for the workflow to work)
- **Work folder**: Use default or specify a custom path

### 4. Install the Runner as a Service (Recommended)

```bash
# Install the service
sudo ./svc.sh install

# Start the service
sudo ./svc.sh start

# Check service status
sudo ./svc.sh status
```

### 5. Verify Ollama Setup

Make sure Ollama is properly configured:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# List available models
ollama list

# Make sure llama3.2 is available
ollama pull llama3.2
```

## Testing the Setup

### 1. Manual Test

Run a simple test to verify everything works:

```bash
cd /path/to/ModPorter-AI
cd ai-engine

# Set environment variables
export USE_OLLAMA=true
export OLLAMA_MODEL=llama3.2
export OLLAMA_BASE_URL=http://localhost:11434
export TEST_LLM_PROVIDER=ollama

# Run integration tests
python -m pytest tests/integration/ -v
```

### 2. Trigger GitHub Actions

1. Push a commit to trigger the workflow
2. Check the **Actions** tab in your GitHub repository
3. Look for the `integration-ollama` job running on your self-hosted runner

## Workflow Matrix Strategy

The updated workflow now includes three test types:

1. **Unit Tests** (`unit`): Run on GitHub-hosted runners (no LLM needed)
2. **Integration Tests with Ollama** (`integration-ollama`): Run on self-hosted runner with `ollama` label
3. **Integration Tests with OpenAI** (`integration-openai`): Run on GitHub-hosted runners (requires API key)

## Troubleshooting

### Runner Not Picking Up Jobs

1. **Check labels**: Ensure your runner has the `ollama` label
2. **Verify runner status**: Check if the runner is online in GitHub Settings
3. **Check service**: `sudo ./svc.sh status`

### Ollama Connection Issues

1. **Check Ollama service**: `curl http://localhost:11434/api/version`
2. **Verify model**: `ollama list | grep llama3.2`
3. **Check firewall**: Ensure port 11434 is accessible

### Permission Issues

1. **Python packages**: Make sure the runner can install packages
2. **Workspace permissions**: Ensure the runner has write access to the workspace
3. **Service permissions**: Run with appropriate user permissions

## Security Considerations

### Self-Hosted Runner Security

⚠️ **Important**: Self-hosted runners can pose security risks, especially for public repositories.

**Recommendations:**
1. **Use for private repositories only** or trusted contributors
2. **Isolate the runner** in a separate environment/container
3. **Regular updates**: Keep the runner software updated
4. **Monitor usage**: Review runner logs regularly
5. **Limit access**: Use specific labels and restrict which workflows can use the runner

### Network Security

1. **Firewall rules**: Only allow necessary ports (11434 for Ollama)
2. **VPN/Private network**: Consider running on a private network
3. **Regular security updates**: Keep the host system updated

## Maintenance

### Updating the Runner

```bash
# Stop the service
sudo ./svc.sh stop

# Update runner (download new version and reconfigure)
./config.sh remove
# Download new version and reconfigure

# Start the service
sudo ./svc.sh start
```

### Updating Ollama Models

```bash
# Update to latest model version
ollama pull llama3.2

# List models to verify
ollama list
```

## Alternative: Docker-based Self-Hosted Runner

For better isolation, consider using a Docker-based runner:

```bash
# Example Dockerfile for self-hosted runner with Ollama
# See GitHub's documentation for containerized runners
```

This setup allows you to run comprehensive integration tests with real LLMs while maintaining security and performance.