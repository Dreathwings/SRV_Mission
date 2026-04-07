#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export MISSION_ENV="${MISSION_ENV:-production}"
export MISSION_CAS_ENABLED="${MISSION_CAS_ENABLED:-true}"
export MISSION_DEV_MODE="${MISSION_DEV_MODE:-false}"

if ! command -v gunicorn >/dev/null 2>&1; then
  echo "gunicorn est requis. Installe les dependances avec: pip install -r requirements.txt" >&2
  exit 1
fi

exec gunicorn \
  --bind "${MISSION_HOST:-0.0.0.0}:${PORT:-6969}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --threads "${WEB_THREADS:-4}" \
  --timeout "${WEB_TIMEOUT:-120}" \
  wsgi:app

