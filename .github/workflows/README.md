# CI/CD workflows

PR feedback runs through **`pr.yml`** (single, paths-filtered, concurrency-cancelled).
Heavy validation runs nightly through **`nightly.yml`**.

## On every PR push

`pr.yml` → at most 9 jobs, only the ones whose paths actually changed:

| Job              | Purpose                                | Trigger condition         | Typical wall-clock |
| ---------------- | -------------------------------------- | ------------------------- | ------------------ |
| `changes`        | paths-filter fan-out                   | always                    | ~10 s              |
| `lint`           | ruff + ruff-format + prettier + bandit | `python` or `frontend`    | ~60–90 s           |
| `backend-tests`  | pytest unit + xdist + coverage         | `backend`                 | ~3–4 min           |
| `ai-engine-tests`| pytest unit + xdist + coverage         | `ai_engine`               | ~5–7 min           |
| `frontend`       | tsc + eslint + vitest + vite build     | `frontend`                | ~3–4 min           |
| `integration`    | sqlite + mocked services (matches old ci.yml) | `backend` or `ai_engine`  | ~2–3 min           |
| `security`       | pip-audit + pnpm audit + Trivy fs      | `python` or `frontend`    | ~60–90 s           |
| `workflow-lint`  | YAML validation                        | `.github/workflows/**`    | ~10 s              |
| `pr-gates`       | aggregator (single status check)       | always                    | ~5 s               |

**Branch-protection check name:** `PR Gates`.

`pr.yml` also runs on push to `main` / `develop` (without cancelling
in-flight runs) so we still get a clean post-merge signal.

## Concurrency model

```yaml
concurrency:
  group: pr-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

Iterative pushes to the same PR cancel the prior run immediately; this is
the single biggest free-runner saving.

## What runs nightly

`nightly.yml` runs on `cron: '17 7 * * *'` and via manual dispatch:

* `codeql` (Python + JavaScript)
* `mutation-python` (mutmut for `backend` and `ai-engine`)
* `mutation-frontend` (stryker)
* `trivy-image` (build + scan Docker images for backend, ai-engine, frontend)
* `ollama-integration` (pulls real `llama3.2`, only on Sundays or explicit
  dispatch with `run_ollama=true`)
* `integration-real-services` (full backend + ai-engine integration suite
  against real PostgreSQL + Redis service containers; covers the
  `@pytest.mark.real_service` tests that PRs skip)
* `nightly-summary`

Each individual nightly job is independently dispatchable — the workflow
inputs (`run_mutation`, `run_codeql`, `run_ollama`, `run_trivy_image`)
let you skip pieces from the GitHub UI.

## cd.yml Kubernetes deploys (opt-in)

`cd.yml` builds Docker images for backend/ai-engine/frontend and pushes
them to GHCR. The downstream `Deploy to Staging (Kubernetes)` and
`Deploy to Production (Kubernetes)` jobs are **opt-in** — they only run
when both:

* `vars.ENABLE_K8S_DEPLOY` is set to `true`
* `secrets.STAGING_KUBECONFIG` / `secrets.PRODUCTION_KUBECONFIG` are configured

The real production deploy lives in `fly-deploy.yml`. The K8s wiring is
preserved for future use; until you set the variable, those jobs cleanly
skip and `cd.yml` ends green after a successful image build.

To enable later:

```bash
gh variable set ENABLE_K8S_DEPLOY --body true
gh secret set STAGING_KUBECONFIG    < /path/to/staging-kubeconfig
gh secret set PRODUCTION_KUBECONFIG < /path/to/production-kubeconfig
```

## Other workflows (unchanged scope)

| File                      | When                              |
| ------------------------- | --------------------------------- |
| `cd.yml`                  | push to `main`, tags `v*`         |
| `fly-deploy.yml`          | push to `main`                    |
| `release.yml`             | push of tags                      |
| `docker-publish.yml`      | release event                     |
| `docs.yml`                | push to `main`                    |
| `security.yml`            | push to `main`/`develop`, weekly  |
| `cache-cleanup.yml`       | weekly                            |
| `beta-smoke-test.yml`     | daily + dispatch                  |
| `load-test.yml`           | weekly + dispatch                 |
| `openapi-contract.yml`    | daily + dispatch                  |
| `depcheck.yml`            | weekly + PR (path-filtered)       |
| `validate-workflows.yml`  | PR (path-filtered)                |
| `claude.yml`              | `@claude` mentions                |
| `rebase-helper.yml`       | dispatch only                     |
| `nightly.yml`             | nightly cron + dispatch           |

## Migration notes (2026-05-15)

The following workflows were folded into `pr.yml` / `nightly.yml`:

* `ci.yml` (1365 lines) → `pr.yml` (paths-filter, lint, backend-tests, ai-engine-tests, frontend, integration, security)
* `ai-quality-gates.yml` (403 lines) → `pr.yml` (lint, backend-tests, integration; coverage gate retained)
* `ci-backend-unit-tests.yml` (171 lines) → `pr.yml::backend-tests`
* `ci-ai-engine-tests.yml` (99 lines) → `pr.yml::ai-engine-tests`
* `build-base-images.yml` (248 lines) — **deleted**. The pre-built `python-base` /
  `node-base` images it produced were unused by `cd.yml` and `deploy.yml`
  (those build straight from `Dockerfile`, not `Dockerfile.optimized`).
  `uv pip sync` against `requirements.lock` is now the install path; it's
  faster than the old base-image trick and needs zero registry maintenance.
* `test-optimization.yml` (173 lines) — **deleted**. Was a manual playground
  for the base-image system that no longer exists.
* `deploy.yml` (453 lines) — **deleted** (2026-05-15). SSH+DockerHub deploy
  that had been failing for days (no DOCKERHUB_USERNAME/SSH_PRIVATE_KEY
  secrets). Real production deploy is `fly-deploy.yml` and image build is
  `cd.yml`. The PR-test jobs in deploy.yml were already redundant with `pr.yml`.

PR triggers were removed from:

* `deploy.yml`, `security.yml`, `docs.yml`, `beta-smoke-test.yml`
  (these were all running redundantly on every PR).

## Lockfiles (`uv pip sync`)

`pr.yml` and `nightly.yml` install Python deps with:

```bash
uv pip sync --system requirements.lock
```

against committed lockfiles:

* `backend/requirements.lock`   (Python 3.11)
* `ai-engine/requirements.lock` (Python 3.12)

To regenerate after changing `requirements*.txt`:

```bash
cd backend   && uv pip compile requirements.txt requirements-dev.txt -o requirements.lock --python-version 3.11
cd ai-engine && uv pip compile requirements.txt requirements-dev.txt -o requirements.lock --python-version 3.12
```

The header comment of each lockfile records the exact regen command.

The six removed workflow files are kept for reference at
`.github/.archived-workflows-2026-05-15/`. GitHub Actions does not scan
that path.
