#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p artifacts
if ! curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  nohup .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 > artifacts/backend.log 2>&1 &
  echo "$!" > artifacts/backend.pid
fi
if ! curl -fsS http://localhost:3000 >/dev/null 2>&1; then
  nohup npm --prefix frontend start > artifacts/frontend.log 2>&1 &
  echo "$!" > artifacts/frontend.pid
fi
for attempt in {1..40}; do
  if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1 && curl -fsS http://localhost:3000/api/health >/dev/null 2>&1; then
    echo 'PayLink frontend, backend, and database are connected.'
    exit 0
  fi
  sleep 1
done
echo 'Startup failed; inspect artifacts/backend.log and artifacts/frontend.log.' >&2
exit 1
