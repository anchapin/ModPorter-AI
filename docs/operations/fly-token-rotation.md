# Fly.io API Token Rotation Runbook

**Issue**: [#1438](https://github.com/anchapin/portkit/issues/1438)
**Audience**: Maintainers with Fly.io org access and write access to `anchapin/portkit` GitHub Actions secrets.

This runbook describes how to rotate the Fly.io API token used by
`.github/workflows/fly-deploy.yml` when `flyctl` reports `unauthorized` before any image build starts.

---

## When to use this runbook

Use this runbook when both Fly.io deploy jobs fail during authentication in the
`Deploy to Fly.io` step.

Expected failure format:

```text
Run superfly/flyctl-actions@master
Error: unauthorized
Error: Process completed with exit code 1.
```

This is the right runbook when:

- The failure appears in `Deploy to Fly.io` (`superfly/flyctl-actions@master`).
- The log stops before any Docker image build output.
- Both staging (`portkit-backend-staging`) and production (`portkit-backend`) fail the same way.
- Re-running the workflow or pushing a new commit produces the same auth error.

This is **not** the right runbook when auth succeeds and a later step fails:

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `Error: unauthorized` before image build | Expired, revoked, or invalid Fly.io token | Use this runbook ([#1438](https://github.com/anchapin/portkit/issues/1438)) |
| Build starts, then dependency resolution fails | Separate dependency conflict | Track [#1439](https://github.com/anchapin/portkit/issues/1439) |
| Deploy succeeds, then health check or smoke test fails | App boot, networking, or runtime problem | Use the incident response runbook in `docs/runbook.md` |
| `app <name> not found` after auth succeeds | Wrong app, org, or token scope | Re-check the app name and token scope |

Find failing workflow runs at:

1. <https://github.com/anchapin/portkit/actions/workflows/fly-deploy.yml>
2. Open a failed `main` run.
3. Open the failed `Deploy <environment>` job.
4. Expand `Deploy to Fly.io` and confirm the `unauthorized` output above.

CLI helper:

```bash
gh run list --repo anchapin/portkit --workflow fly-deploy.yml --limit 10
gh run view <run-id> --repo anchapin/portkit --log-failed
```

---

## Prerequisites

Before rotating the token, confirm you have:

- `flyctl` installed locally.
- A local Fly.io session for the account or org that owns the PortKit apps:
  ```bash
  fly auth login
  fly auth whoami
  ```
- `gh` CLI authenticated against `anchapin/portkit` with `repo` scope.
- Write access to repository secrets in `anchapin/portkit`.
- Membership in the Fly.io org that owns `portkit-backend-staging` and `portkit-backend`.

Do not continue if you lack repo-secret write access or Fly.io org access; ask a maintainer with both permissions to perform the manual steps.

---

## Step 1 — Verify the token is bad

GitHub does not let you retrieve an existing secret value. First confirm that the secret name exists, then test the token value from the Fly.io dashboard or your password manager.

```bash
# Confirm the secret exists; this does NOT print the secret value.
gh secret list --repo anchapin/portkit | grep FLY_API_TOKEN

# Or read the token from your local Fly.io dashboard at:
# https://fly.io/dashboard/personal/tokens
FLY_API_TOKEN="<paste token here>" fly auth whoami
```

Safer local variant that avoids echoing the token into shell history:

```bash
read -s -p "Paste current FLY_API_TOKEN: " CURRENT_TOKEN; echo
FLY_API_TOKEN="$CURRENT_TOKEN" fly auth whoami
unset CURRENT_TOKEN
```

Expected healthy output:

```text
<your-fly-account-email@example.com>
```

Failing output that confirms this runbook applies:

```text
Error: unauthorized
```

or:

```text
Error: token has expired
```

If `fly auth whoami` succeeds with the token you tested, but GitHub Actions still fails with `unauthorized`, the value stored in GitHub is probably different from the token you tested. Continue to Step 3 to overwrite the repository secret with a known-good token.

---

## Step 2 — Create new token(s)

Choose one token strategy.

### Option A (recommended) — per-app deploy tokens

Use per-app deploy tokens for least privilege **when the workflow can read per-app secrets**.

```bash
fly tokens create deploy --app portkit-backend-staging --expiry 168h
fly tokens create deploy --app portkit-backend         --expiry 168h
```

`168h` = 7 days. Short expiry limits blast radius if a token leaks, but it requires a reliable reminder. Prefer short expiry plus a calendar reminder over `--expiry never`.

Trade-off summary:

| Expiry choice | Benefit | Risk / cost |
| --- | --- | --- |
| `--expiry 168h` | Limits leaked-token lifetime to 7 days | Requires weekly rotation discipline |
| Longer fixed expiry | Fewer rotations | Larger leak window |
| `--expiry never` | No scheduled rotations | Token remains usable until manually revoked |

Recommendation: use `--expiry 168h` and schedule the next rotation about 3 days before expiry.

> `# TODO verify against flyctl docs` — confirm the supported `--expiry` duration syntax before running if your local `flyctl` version differs from the one previously used by the team.

### Option B — single org token (only if deploy tokens are not viable)

Use a single org token only when per-app deploy tokens are not viable, or when the workflow has not yet been refactored to select a different secret for staging and production.

```bash
fly tokens create org <org-slug>
```

This is broader than a per-app deploy token. Treat it as higher risk and rotate it on a short, documented cadence.

---

## Step 3 — Store new token(s) in GitHub Secrets

Do not paste token values directly into commands that will be saved in shell history. Use `read -s`, write the secret with `gh secret set`, then `unset` the shell variable.

### If using per-app deploy tokens

Store both per-app tokens:

```bash
read -s -p "Staging deploy token: " FLY_TOKEN_STAGING; echo
gh secret set FLY_API_TOKEN_STAGING --repo anchapin/portkit --body "$FLY_TOKEN_STAGING"
unset FLY_TOKEN_STAGING

read -s -p "Production deploy token: " FLY_TOKEN_PROD; echo
gh secret set FLY_API_TOKEN_PROD --repo anchapin/portkit --body "$FLY_TOKEN_PROD"
unset FLY_TOKEN_PROD
```

Verify the names exist; GitHub will not print the values:

```bash
gh secret list --repo anchapin/portkit | grep -E '^FLY_API_TOKEN(_STAGING|_PROD)?\b'
```

**Important:** the current workflow in `origin/main` reads only `secrets.FLY_API_TOKEN`. Creating `FLY_API_TOKEN_STAGING` and `FLY_API_TOKEN_PROD` is not enough by itself unless the workflow has been refactored to use them. Until that refactor lands, use Option B for the immediate production fix, or complete the workflow refactor before relying on per-app deploy tokens.

Do **not** set the legacy `FLY_API_TOKEN` to only one app's deploy token and expect both matrix entries to work; a staging-only token will not be appropriate for production, and a production-only token will not be appropriate for staging.

### If using the single-token option

```bash
read -s -p "Fly.io org token: " FLY_TOKEN; echo
gh secret set FLY_API_TOKEN --repo anchapin/portkit --body "$FLY_TOKEN"
unset FLY_TOKEN
```

If you accidentally typed a token value on the command line, remove it from shell history immediately.

---

## Step 4 — Verify the rotation

Re-run the failed workflow:

```bash
gh workflow run fly-deploy.yml --repo anchapin/portkit --ref main
gh run watch --repo anchapin/portkit
```

In the GitHub Actions UI:

1. Open the new run at <https://github.com/anchapin/portkit/actions/workflows/fly-deploy.yml>.
2. Open `Deploy staging` and expand `Deploy to Fly.io`.
3. Confirm the step gets past auth: `Error: unauthorized` is gone and deploy/build output begins.
4. Repeat for `Deploy production`.

If auth succeeds but production later fails during dependency resolution, continue tracking [#1439](https://github.com/anchapin/portkit/issues/1439). That is a separate failure mode and is not fixed by rotating the Fly.io token.

---

## Step 5 — Schedule the next rotation

Do not rely on memory. After Step 4 succeeds:

1. Add a calendar reminder to rotate the Fly.io deploy token(s) about 3 days before expiry.
2. If the team has a secrets-management or monitoring tool, configure a Dependabot-style alert for expiring tokens.
3. Update the `Last rotated:` line at the bottom of this runbook in a follow-up PR.

---

## Appendix — Why per-app deploy tokens > org tokens

Per-app deploy tokens are safer because they follow least privilege. If a staging token leaks, the blast radius is limited to the staging app instead of the whole Fly.io org. Per-app tokens are also easier to revoke individually and make audit trails clearer because each token maps to one deploy target. Org tokens are simpler for an unrefactored single-secret workflow, but they should be treated as broader, higher-risk credentials.

---

## Follow-up TODO — workflow refactor for per-app secrets

The current workflow uses one secret for both apps:

```yaml
env:
  FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

A follow-up workflow change should let staging use `FLY_API_TOKEN_STAGING` and production use `FLY_API_TOKEN_PROD`, while falling back to `FLY_API_TOKEN` for backward compatibility.

The original sketch uses a matrix-provided secret name:

```yaml
matrix:
  include:
    - environment: staging
      app_name: portkit-backend-staging
      api_url: https://staging-api.portkit.cloud
      token_secret_name: FLY_API_TOKEN_STAGING
    - environment: production
      app_name: portkit-backend
      api_url: https://api.portkit.cloud
      token_secret_name: FLY_API_TOKEN_PROD

- name: Deploy to Fly.io
  uses: superfly/flyctl-actions@master
  env:
    # Prefer per-app token; fall back to legacy single token for backward compat.
    FLY_API_TOKEN: ${{ secrets[matrix.token_secret_name] || secrets.FLY_API_TOKEN }}
  with:
    args: "deploy --app ${{ matrix.app_name }} --remote-only"
```

Do not merge that workflow change until it has been validated in a real GitHub Actions runner; dynamic secret indexing is not supported in every context. If dynamic indexing fails, use explicit staging/production deploy steps with static secret names instead.

---

## Related issues

- [#1438](https://github.com/anchapin/portkit/issues/1438) — `ops(deploy): rotate FLY_API_TOKEN — flyctl returns 'unauthorized' on every main deploy`.
- [#1439](https://github.com/anchapin/portkit/issues/1439) — separate dependency-resolution failure mode that appears after Fly.io auth succeeds.

---

**Last rotated:** _never (initial runbook)_ — update after Step 4 succeeds, using `YYYY-MM-DD by <github-handle> (next rotation due YYYY-MM-DD)`.
