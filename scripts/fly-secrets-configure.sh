#!/usr/bin/env bash
# setup-fly-secrets.sh — Configure all required Fly.io secrets for modporter.ai
#
# Run this ONCE before first deploy, and whenever you rotate a secret.
# Prerequisites: fly CLI authenticated (`fly auth login`) and app selected.
#
# Usage:
#   ./scripts/setup-fly-secrets.sh [--app <app-name>]
#
# Each secret is generated or prompted interactively.
# Secrets are NEVER written to disk or committed to git.

set -euo pipefail

APP_FLAG=""
if [[ "${1:-}" == "--app" && -n "${2:-}" ]]; then
  APP_FLAG="--app $2"
fi

FLY="fly $APP_FLAG"

echo "=== ModPorter-AI Fly.io Secrets Setup ==="
echo ""

# ── Helper functions ──────────────────────────────────────────────────────────

generate_key() {
  openssl rand -base64 32
}

prompt_or_generate() {
  local name="$1"
  local description="$2"
  local generated
  generated="$(generate_key)"

  echo "  $name — $description"
  echo "  Auto-generated value: ${generated:0:8}... (press Enter to use, or type a custom value)"
  read -r -p "  > " user_input
  echo ""

  if [[ -z "$user_input" ]]; then
    echo "$generated"
  else
    echo "$user_input"
  fi
}

prompt_required() {
  local name="$1"
  local description="$2"
  local value=""

  while [[ -z "$value" ]]; do
    echo "  $name — $description"
    read -r -p "  > " value
    if [[ -z "$value" ]]; then
      echo "  ERROR: $name is required. Please enter a value."
    fi
  done
  echo ""
  echo "$value"
}

# ── Secrets ───────────────────────────────────────────────────────────────────

echo "--- Step 1/6: Application Secret Keys ---"
SECRET_KEY="$(prompt_or_generate SECRET_KEY "Main application secret key (32+ chars)")"
JWT_SECRET_KEY="$(prompt_or_generate JWT_SECRET_KEY "JWT signing key (32+ chars, different from SECRET_KEY)")"

echo "--- Step 2/6: Database ---"
DB_PASSWORD="$(prompt_or_generate DB_PASSWORD "PostgreSQL password (used in DATABASE_URL)")"
DATABASE_URL="$(prompt_required DATABASE_URL "Full async DATABASE_URL (e.g., postgresql+asyncpg://postgres:<password>@<host>:5432/modporter)")"

echo "--- Step 3/6: AI API Keys ---"
OPENAI_API_KEY="$(prompt_required OPENAI_API_KEY "OpenAI API key (sk-...)")"
ANTHROPIC_API_KEY="$(prompt_required ANTHROPIC_API_KEY "Anthropic API key (sk-ant-...)")"

echo "--- Step 4/6: Monitoring ---"
SENTRY_DSN="$(prompt_required SENTRY_DSN "Sentry DSN (https://...@sentry.io/...)")"
GRAFANA_ADMIN_PASSWORD="$(prompt_or_generate GRAFANA_ADMIN_PASSWORD "Grafana admin password")"

echo "--- Step 5/6: CORS ---"
echo "  CORS_ORIGINS — Comma-separated list of allowed origins"
echo "  Default: https://modporter.ai,https://www.modporter.ai"
read -r -p "  > " CORS_ORIGINS
CORS_ORIGINS="${CORS_ORIGINS:-https://modporter.ai,https://www.modporter.ai}"
echo ""

echo "--- Step 6/6: Email (optional) ---"
echo "  SMTP_PASSWORD — Leave blank to skip email configuration"
read -r -p "  > " SMTP_PASSWORD
echo ""

# ── Apply to Fly.io ───────────────────────────────────────────────────────────

echo "=== Applying secrets to Fly.io (values are NOT echoed) ==="

$FLY secrets set \
  SECRET_KEY="$SECRET_KEY" \
  JWT_SECRET_KEY="$JWT_SECRET_KEY" \
  DB_PASSWORD="$DB_PASSWORD" \
  DATABASE_URL="$DATABASE_URL" \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  SENTRY_DSN="$SENTRY_DSN" \
  GRAFANA_ADMIN_PASSWORD="$GRAFANA_ADMIN_PASSWORD" \
  CORS_ORIGINS="$CORS_ORIGINS" \
  ENVIRONMENT="production"

if [[ -n "$SMTP_PASSWORD" ]]; then
  $FLY secrets set SMTP_PASSWORD="$SMTP_PASSWORD"
fi

echo ""
echo "=== Done! Verifying secrets are set ==="
$FLY secrets list

echo ""
echo "=== Next Steps ==="
echo "1. Deploy: fly deploy"
echo "2. Verify startup logs: fly logs"
echo "3. Run smoke test: curl https://modporter.ai/api/v1/health"
