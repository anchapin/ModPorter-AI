# Branch Protection Configuration

## Required Status Checks for PRs

To ensure code quality, the following status checks are required for all pull requests targeting `main` and `develop` branches:

### CI Workflow Status Checks
- `integration-tests (backend)` - Backend integration tests
- `integration-tests (ai-engine)` - AI Engine integration tests  
- `integration-tests (integration)` - Cross-service integration tests
- `frontend-tests (unit)` - Frontend unit tests
- `frontend-tests (build)` - Frontend build verification
- `frontend-tests (lint)` - Frontend linting
- **`coverage-check` - Test coverage verification (≥80% required)**
- `performance-monitoring` - CI performance and cache monitoring

### Coverage Requirements

**Minimum Coverage: 80%**

Both backend and AI Engine must maintain at least 80% test coverage. The `coverage-check` job will:

1. Run comprehensive test suites with coverage reporting
2. Parse coverage XML files to extract exact percentages
3. Fail the build if any component falls below 80%
4. Generate a summary report in the PR

### Coverage Enforcement

The CI workflow now enforces 80% coverage through:
- `--cov-fail-under=80` flag in pytest configuration
- Explicit threshold checking in the coverage-check job
- Error messages with exact coverage percentages when thresholds aren't met
- GitHub Step Summary with pass/fail status for each component

### Adding to Branch Protection

To enable this in your repository:

1. Go to Settings → Branches → Branch protection rule
2. Select `main` and `develop` branches
3. Enable "Require status checks to pass before merging"
4. Add all the status checks listed above
5. Enable "Require branches to be up to date before merging"

### Coverage Report Locations

Coverage reports are uploaded as artifacts:
- `coverage-reports` artifact contains:
  - XML reports for programmatic access
  - HTML reports for detailed viewing
  - JSON reports for integration with other tools

Reports are retained for 7 days and can be downloaded from the Actions tab.
