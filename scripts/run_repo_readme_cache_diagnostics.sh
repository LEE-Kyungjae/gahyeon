#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SQL_FILE="${ROOT_DIR}/scripts/sql/repo_readme_cache_diagnostics.sql"

if [[ ! -f "${SQL_FILE}" ]]; then
  echo "SQL file not found: ${SQL_FILE}" >&2
  exit 1
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  echo "[info] running diagnostics via DATABASE_URL"
  psql "${DATABASE_URL}" -f "${SQL_FILE}"
  exit 0
fi

if [[ -n "${POSTGRES_PROD_HOST:-}" && -n "${POSTGRES_PROD_PORT:-}" && -n "${POSTGRES_PROD_USERNAME:-}" && -n "${POSTGRES_PROD_PASSWORD:-}" ]]; then
  echo "[info] running diagnostics via POSTGRES_PROD_* env vars"
  PGPASSWORD="${POSTGRES_PROD_PASSWORD}" psql \
    -h "${POSTGRES_PROD_HOST}" \
    -p "${POSTGRES_PROD_PORT}" \
    -U "${POSTGRES_PROD_USERNAME}" \
    -d gahyeonbot \
    -f "${SQL_FILE}"
  exit 0
fi

cat >&2 <<'EOF'
Missing DB connection variables.
Provide one of:
1) DATABASE_URL=postgres://user:pass@host:port/gahyeonbot
2) POSTGRES_PROD_HOST, POSTGRES_PROD_PORT, POSTGRES_PROD_USERNAME, POSTGRES_PROD_PASSWORD
EOF
exit 1
