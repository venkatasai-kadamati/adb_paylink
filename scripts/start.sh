#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/runtime.sh
exec .venv/bin/python scripts/start.py "$@"
