# AI Agent Commits

This document describes the AI-friendly commit conventions and workflows configured for the ModPorter-AI project.

## Overview

The project uses **conventional commits** to enable:
- Automated changelog generation
- Clear commit history for AI analysis
- Consistent message formatting
- Automated commit validation
- AI agent identification

## Setup

### Automatic Setup

Run the setup script once:

```bash
pnpm run setup-ai-commits
```

This will:
1. Install commitlint dependencies
2. Configure husky git hooks
3. Set up the git message template
4. Enable AI agent signing configuration

### Manual Installation

```bash
# Install dependencies
pnpm add -D @commitlint/cli @commitlint/config-conventional husky

# Initialize husky
npx husky install

# Configure git message template
git config commit.template .gitmessage

# Enable AI agent signing
git config user.ai-agent true
```

## Commit Format

All commits must follow the **conventional commits** specification:

```
<type>: <subject> (#issue-number)

<body>

<footer>
```

### Type

Required. Must be one of:

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `style` | Changes that don't affect code meaning (formatting, whitespace) |
| `perf` | Code change that improves performance |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `chore` | Build process, dependency, or tooling changes |
| `ci` | CI/CD configuration or script changes |
| `revert` | Reverts a previous commit |

### Subject

- Use imperative mood ("add feature", not "added feature")
- Capitalize the first letter
- Do not end with a period
- Limit to 50 characters
- Include issue number in parentheses if applicable

### Body

- Explain **what** and **why**, not how
- Wrap lines at 72 characters
- Separate from subject with a blank line
- Optional but recommended for non-trivial commits

### Footer

- Reference issues: `Closes #123`, `Fixes #456`, `Refs #789`
- Note breaking changes: `BREAKING CHANGE: description`
- Multiple footers allowed

## Examples

### Simple Bug Fix

```
fix: prevent racing condition in auth handler (#689)

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Closes #123
```

### New Feature

```
feat: add retry mechanism for API calls (#234)

Implement exponential backoff strategy for failed API requests.
Configurable retry count and base delay.

- Max 3 retries by default
- Exponential backoff: 100ms, 200ms, 400ms
- Respects Retry-After header

Closes #234
```

### Documentation

```
docs: update API authentication section (#567)
```

### Chore

```
chore: upgrade dependencies (#890)

Update all npm packages to latest stable versions.
```

## AI Agent Identification

AI agents can identify themselves in commits:

```bash
# Set globally
git config --global user.ai-agent true

# Set for this repository
git config user.ai-agent true

# Check configuration
git config user.ai-agent
```

When set, the commit author will include AI agent metadata.

## Commit Hooks

### prepare-commit-msg

Automatically prepends issue numbers from branch names:
- Branch: `feature/689-enable-ai-commits` → Commit: `[#689] feat: ...`

### commit-msg

Validates commit messages against conventional commit rules:
- Rejects commits that don't follow the format
- Provides helpful error messages
- Can be bypassed with `--no-verify` (not recommended for main branches)

## Validation Rules

Commits are validated against:

1. **Type**: Must be from approved list
2. **Subject**: No period at end, max 100 characters
3. **Case**: Type in lowercase, subject in sentence case
4. **Headers**: Max 100 characters
5. **Body**: Max 100 characters per line, blank line before
6. **Footer**: Blank line before, max 100 characters per line

## CI Integration

The CI/CD pipeline validates all commits using commitlint. Commits that fail validation will cause the build to fail.

To check locally before pushing:

```bash
# Check last commit
npx commitlint --from HEAD~1

# Check entire branch
npx commitlint --from origin/main..HEAD
```

## IDE Integration

### VS Code

Install the [Conventional Commits](https://marketplace.visualstudio.com/items?itemName=vivaxy.vscode-conventional-commits) extension for visual commit guidance.

### JetBrains IDEs (IntelliJ, WebStorm, etc.)

The built-in commit dialog respects `.gitmessage` template. Enable it in:
- Settings → Version Control → Git → Use commit template

## Resources

- [Conventional Commits](https://www.conventionalcommits.org/) - Specification
- [commitlint](https://commitlint.js.org/) - Tool documentation
- [Husky](https://typicode.github.io/husky/) - Git hooks documentation

## Troubleshooting

### Commit rejected by commitlint

Check the error message for what rule was violated. Common issues:

```
# Too long subject
Error: header must not be longer than 100 characters

# Missing type
Error: type is empty

# Wrong type
Error: type must be one of [...]
```

### Bypass validation (emergency only)

```bash
# Not recommended - use only for emergency hotfixes
git commit --no-verify
```

### Reset git config

```bash
# Reset to defaults
git config --unset commit.template
git config --unset user.ai-agent
```

## Contributing

When submitting PRs, ensure:
1. All commits follow conventional commits format
2. Commits are logically organized
3. Commit messages are clear and descriptive
4. Issue references are included in commit messages and PR description

For more details, see [CONTRIBUTING.md](../CONTRIBUTING.md).
