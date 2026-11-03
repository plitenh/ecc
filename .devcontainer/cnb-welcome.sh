#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/workspace}"
cd "$PROJECT_ROOT"

uv sync \
  --no-build-isolation-package ecc-dreamplace \
  --no-build-isolation-package ecc-tools-bin \
  --verbose

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "ECC cloud workspace ready: $(command -v python)"
