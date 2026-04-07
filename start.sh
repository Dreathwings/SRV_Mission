#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

for env_file in ".env.production.local" ".env.production" ".env"; do
  if [ -f "$env_file" ]; then
    set -a
    # shellcheck disable=SC1090
    . "./$env_file"
    set +a
    break
  fi
done

export MISSION_ENV="${MISSION_ENV:-production}"
export MISSION_CAS_ENABLED="${MISSION_CAS_ENABLED:-true}"
export MISSION_DEV_MODE="${MISSION_DEV_MODE:-false}"

if ! command -v gunicorn >/dev/null 2>&1; then
  echo "gunicorn est requis. Installe les dependances avec: pip install -r requirements.txt" >&2
  exit 1
fi

required_vars=(
  MISSION_SECRET_KEY
  MISSION_DB_PASSWORD
  MISSION_CAS_DB_PASSWORD
  MISSION_PUBLIC_BASE_URL
)

for var_name in "${required_vars[@]}"; do
  if [ -z "${!var_name:-}" ]; then
    echo "Variable requise manquante: $var_name" >&2
    echo "Cree .env.production a partir de .env.production.example ou exporte la variable avant de lancer start.sh." >&2
    exit 1
  fi
done

exec gunicorn \
  --bind "${MISSION_HOST:-0.0.0.0}:${PORT:-6969}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --threads "${WEB_THREADS:-4}" \
  --timeout "${WEB_TIMEOUT:-120}" \
  wsgi:app
