#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/runtime.sh
if [[ -z "${PYTHON_BIN:-}" ]]; then
  PYTHON_BIN="$(command -v python3.12 || command -v python3)"
fi
if [[ ! -x .venv/bin/python ]]; then "$PYTHON_BIN" -m venv .venv; fi
.venv/bin/python -m pip install --cache-dir "$PWD/.cache/pip" -r backend/requirements.txt
npm --cache "$PWD/.cache/npm" ci --prefix frontend
.venv/bin/python scripts/local_db.py
.venv/bin/python scripts/migrate.py
.venv/bin/python scripts/seed.py --demo
npm --cache "$PWD/.cache/npm" run build --prefix frontend
