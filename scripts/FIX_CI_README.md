# Fix Failing CI Checks

This directory contains the `fix-failing-ci-checks` command for automatically detecting, diagnosing, and fixing failing CI checks for pull requests.

## Installation

The command is automatically available as part of the ModPorter AI CLI.

## Usage

### As a standalone script:

**Linux/macOS:**
```bash
./scripts/fix-failing-ci-checks
```

**Windows:**
```cmd
scripts\fix-failing-ci-checks.bat
```

### As part of the ModPorter CLI:

```bash
python -m modporter.cli fix-ci
```

## Prerequisites

- Must be in a git repository with a GitHub remote
- Must have the GitHub CLI (`gh`) installed and authenticated
- Must have local test environment set up (pytest, etc.)

## Command Options

```bash
fix-failing-ci-checks [OPTIONS]

Options:
  --repo-path PATH    Path to the repository (default: current directory)
  -v, --verbose       Enable verbose logging
  --version           Show version and exit
  --help              Show help message
```

## How It Works

When executed, the command will:

1. **Detect Current PR**: Automatically find the pull request associated with the current branch
2. **Identify Failing Jobs**: Check GitHub Actions/CI for any failing jobs
3. **Download Logs**: Fetch detailed logs from all failing jobs
4. **Analyze Failures**: Parse logs to categorize and identify specific failure types:
   - Test failures
   - Linting errors
   - Type checking errors  
   - Build errors
   - Dependency issues
5. **Apply Automatic Fixes**: Where possible, automatically fix issues:
   - Format code with `black`
   - Sort imports with `isort`
   - Remove unused imports with `autoflake`
   - Install missing dependencies
6. **Create Backup**: Before making changes, create a backup branch
7. **Commit Changes**: Commit fixes with descriptive commit messages
8. **Verify Fixes**: Run local tests to ensure fixes work
9. **Rollback if Needed**: If verification fails, automatically rollback changes

## Supported Fix Types

### Automatic Fixes

- **Linting Errors**: Uses `black`, `isort`, and `autoflake` to fix formatting and import issues
- **Dependency Issues**: Installs missing dependencies from requirements files
- **Import Errors**: Attempts to resolve missing module imports

### Manual Fixes Required

- **Type Errors**: Mypy and other type checking errors need manual fixing
- **Test Failures**: Test logic errors require manual investigation
- **Build Errors**: Complex build issues need manual resolution

## Configuration

The command respects the following configuration files:
- `pyproject.toml` - Test and linting configuration
- `requirements*.txt` - Python dependencies
- `.github/workflows/` - CI job definitions
- `pytest.ini` - Pytest configuration
- `.flake8` - Flake8 linting rules
- `mypy.ini` - MyPy type checking rules

## Example Output

```
🔧 Starting CI fix process...
Detected PR #123: "Add new feature"
Found 3 failing jobs:
  - CI (pytest): test-job - failure
  - Lint (flake8): lint-job - failure  
  - Type Check (mypy): type-check-job - failure

📊 Failure Analysis:
  test_failures: 2 issues
  linting_errors: 5 issues
  type_errors: 3 issues

Created backup branch: ci-fix-backup-1699164000
Applied black formatting
Applied isort formatting
Applied autoflake cleanup
Fixed dependency issues
Fixed linting errors with auto-formatters
Fixed dependency issues
Type errors identified (manual fixing required)
Test failures identified (manual fixing required)
Committed changes: fix(ci): automated fixes for PR #123
  - Fixed linting errors with auto-formatters
  - Fixed dependency issues
  - Type errors identified (manual fixing required)
  - Test failures identified (manual fixing required)

🧪 Running verification tests...
Running: pytest --cov=quantchain tests/
✅ pytest --cov=quantchain tests/ passed
Running: flake8 quantchain tests/
✅ flake8 quantchain tests/ passed
Running: mypy quantchain
❌ mypy quantchain failed

⚠️  Automatic verification failed. Manual review required.
📝 Changes were rolled back to maintain branch stability
```

## Error Handling

- **No PR Found**: Prompts user to create a PR first
- **gh CLI Missing**: Provides installation instructions
- **Automatic Fix Failure**: Provides manual fix instructions
- **Verification Failure**: Rolls back all changes to maintain branch stability

## Tips

1. **Run on Feature Branches**: Always use this on feature branches, not main/master
2. **Review Changes**: After running, review the automatic fixes before pushing
3. **Manual Follow-up**: Some issues require manual fixing after automatic processing
4. **Backup Safety**: The command always creates a backup before making changes

## Troubleshooting

### GitHub CLI Not Found
Install the GitHub CLI:
```bash
# macOS
brew install gh

# Ubuntu/Debian
sudo apt install gh

# Windows
# Download from https://cli.github.com/
```

### Authentication Required
Authenticate with GitHub:
```bash
gh auth login
```

### Missing Python Tools
Install required tools:
```bash
pip install black isort autoflake pytest flake8 mypy
```

## Contributing

To extend the command with additional fix types:

1. Add new pattern detection in `analyze_failure_patterns()`
2. Implement fix logic in corresponding `fix_*()` method
3. Update verification in `run_verification_tests()`
4. Test with various failure scenarios

## License

This command is part of the ModPorter AI project and follows the same license terms.
