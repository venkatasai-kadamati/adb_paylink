#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
"${PYTHON_BIN:-python3}" -m venv .venv
.venv/bin/python -m pip install --cache-dir "$PWD/.cache/pip" -r backend/requirements.txt
npm --cache "$PWD/.cache/npm" ci --prefix frontend
.venv/bin/python scripts/local_db.py
.venv/bin/python scripts/migrate.py
.venv/bin/python scripts/seed.py --demo
npm --cache "$PWD/.cache/npm" run build --prefix frontend
