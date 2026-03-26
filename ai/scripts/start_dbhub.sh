#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/.env"
  set +a
fi

PORT="${DBHUB_PORT:-8080}"

if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then
  echo "DBHub already running on port ${PORT}"
  exit 0
fi

cd "$PROJECT_ROOT"
exec dbhub --transport http --port "$PORT" --config "$PROJECT_ROOT/dbhub.toml"
