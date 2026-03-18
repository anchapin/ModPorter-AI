# Local CI Execution with act CLI

This document describes how to run GitHub Actions workflows locally using the [act CLI](https://github.com/nektos/act) tool.

## Installation

Install act CLI on your system:

```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows
choco install act-cli
```

## Configuration

The repository includes an `.actrc` file with default settings:

- Uses `ghcr.io/catthehacker/ubuntu:full-latest` as the container image
- Enables offline mode for action caching
- Empty secrets that can be configured via environment

## Running Workflows Locally

### Basic Usage

```bash
# List all available workflows
act --list

# Run CI workflow on push event
act push

# Run CI workflow on pull request
act pull_request

# Run a specific job
act --job integration-tests
```

### Setting GitHub Token

Some workflows require a GitHub token. Set it via environment:

```bash
export GITHUB_TOKEN=your_github_token_here
act push
```

Or pass it directly:

```bash
act push -s GITHUB_TOKEN=$GITHUB_TOKEN
```

## Validation

Run the validation script to verify workflow syntax:

```bash
bash scripts/test-act-local-ci.sh
```

This validates that all workflows can be parsed and executed by the act CLI.

## Troubleshooting

### Actions not found

If you see errors about missing actions, ensure you're using `--action-offline-mode` (already configured in `.actrc`) or have the actions cached.

### Docker issues

Make sure Docker is running and you have sufficient permissions:

```bash
docker ps
```

### Secret errors

If workflows fail due to missing secrets, pass them via `-s` flag:

```bash
act push -s SECRET_NAME=value
```
