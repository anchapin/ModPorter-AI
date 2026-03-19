# Commit Review Prompt

The repository has significant uncommitted changes that need to be reviewed and committed in logical groups.

## Current State

- **40 modified files** (net: -3,424 lines removed, +1,328 lines added)
- **80+ untracked files** (new files not yet tracked by git)

## What's Needed

Review the uncommitted changes and organize them into logical commits. The changes appear to include:

### 1. Planning Artifacts (Untracked)
- Phase summaries and plans for phases 04, 07, 10, 11
- New milestone directories (v3.0, v4.2)

### 2. AI Engine Changes (Modified + Untracked)
- Refactored services (many services deleted or significantly modified)
- New agent_metrics modules
- New config files (degradation_config.yaml, timeouts.yaml, validation_config.yaml)
- New engines (coverage_metrics, regression_engine, reporting_engine)
- New finetuning modules
- Test files

### 3. Backend Changes (Modified)
- New API endpoints (analytics.py, alerting.py, model_deployment.py, training_review.py)
- New services (alerting_service.py, error_recovery.py)
- Schema updates (database/schema.sql)

### 4. Frontend Changes (Modified)
- New pages (Analytics, Pricing, FAQ, VisualEditorPage)
- New components (FeedbackSurvey, ModelDeployment, TeamManagement, TrainingReview)
- Onboarding modal

### 5. Configuration Changes (Modified)
- pytest.ini updates
- State tracking files (.factory/tasks.md, .planning/STATE.md)

## Action Required

1. **Review changes** - Use `git diff` to examine modifications
2. **Group into logical commits** - Consider committing by feature/area:
   - Commit 1: Phase planning artifacts
   - Commit 2: AI Engine refactoring (services restructure)
   - Commit 3: New AI Engine features (agent_metrics, config, engines)
   - Commit 4: Backend API additions
   - Commit 5: Frontend features
   - Commit 6: Configuration and testing
3. **Test after each commit** - Ensure the code still works
4. **Write descriptive commit messages** - Follow conventional commits format

## Git Commands to Use

```bash
# Review modified files
git diff --stat

# Review untracked files
git status --short | grep "^??"

# Stage and commit logical groups
git add <files>
git commit -m "feat(scope): description"
```
