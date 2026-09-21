#!/usr/bin/env bash
# Run lit against test/lit (checked-in lit.cfg.py).
# Usage: ci_signoff_lit.sh [lit-args...]
# Env: ECC_REPO_ROOT, PYTHON, FILECHECK, LIT,
#      ECC_EXPORT_SIGNOFF_CSV, ECC_MATERIALIZE_READY,
#      ECC_SIGNOFF_CSV_SPEC, ECC_TEST_WORKSPACE

set -euo pipefail

root="${ECC_REPO_ROOT:-$PWD}"
export ECC_REPO_ROOT="$root"

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ECC_EXPORT_SIGNOFF_CSV="${ECC_EXPORT_SIGNOFF_CSV:-$here/export_signoff_csv.sh}"
export ECC_MATERIALIZE_READY="${ECC_MATERIALIZE_READY:-$here/materialize_signoff_workspace.sh}"
export FILECHECK="${FILECHECK:-filecheck}"
export LIT="${LIT:-lit}"

if [[ -n "${PYTHON:-}" ]]; then
  py="$PYTHON"
elif [[ -x "$root/.venv/bin/python" ]]; then
  py="$root/.venv/bin/python"
else
  py="python3"
fi
export PYTHON="$py"
export PYTHONPATH="$root${PYTHONPATH:+:$PYTHONPATH}"

suite="$root/test/lit"
if [[ ! -f "$suite/lit.cfg.py" || ! -d "$suite/cases" ]]; then
  echo "error: missing checked-in lit suite under $suite" >&2
  exit 1
fi

exec "$LIT" -v "$suite" "$@"
