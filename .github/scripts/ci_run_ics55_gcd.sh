#!/usr/bin/env bash
# Run rtl2gds through a packaged ecc binary (default: ics55 gcd fixture).
#
# Usage:
#   ci_run_ics55_gcd.sh --ecc PATH
#     [--project-dir DIR] [--pdk-root DIR] [--workspace-name NAME]
#     [--ecc-toml PATH] [--rtl PATH ...]
#
# Env: ECC_BIN, ECC_REPO_ROOT
#
# --ecc-toml / repeated --rtl make it easier to batch other designs later
# without rewriting the driver.

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ci_run_ics55_gcd.sh --ecc PATH [--project-dir DIR] [--pdk-root DIR]
                           [--workspace-name NAME] [--ecc-toml PATH] [--rtl PATH ...]
Env: ECC_BIN (alternative to --ecc), ECC_REPO_ROOT
USAGE
  exit 2
}

ecc="${ECC_BIN:-}"
project_dir="ci-artifacts/gcd"
pdk_root=""
workspace_name="default"
ecc_toml=""
rtl_paths=()
root="${ECC_REPO_ROOT:-$PWD}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ecc) ecc="${2:?}"; shift 2 ;;
    --project-dir) project_dir="${2:?}"; shift 2 ;;
    --pdk-root) pdk_root="${2:?}"; shift 2 ;;
    --workspace-name) workspace_name="${2:?}"; shift 2 ;;
    --ecc-toml) ecc_toml="${2:?}"; shift 2 ;;
    --rtl) rtl_paths+=("${2:?}"); shift 2 ;;
    -h|--help) usage ;;
    *) echo "unknown arg: $1" >&2; usage ;;
  esac
done

[[ -n "$ecc" ]] || { echo "missing --ecc / ECC_BIN" >&2; exit 2; }
[[ -x "$ecc" ]] || { echo "ecc not executable: $ecc" >&2; exit 1; }

if [[ -z "$pdk_root" ]]; then
  pdk_root="$(cd "$root/.." && pwd)/pdk/icsprout55-pdk"
  [[ -d "$pdk_root" ]] || pdk_root="$(cd "$PWD/.." && pwd)/pdk/icsprout55-pdk"
fi
[[ -d "$pdk_root" ]] || { echo "PDK root missing: $pdk_root" >&2; exit 1; }

if [[ -n "$ecc_toml" && ! -f "$ecc_toml" ]]; then
  echo "ecc.toml missing: $ecc_toml" >&2
  exit 1
fi

if [[ ${#rtl_paths[@]} -eq 0 ]]; then
  rtl_paths=("$root/test/fixtures/gcd/gcd.v")
fi
for rtl in "${rtl_paths[@]}"; do
  [[ -f "$rtl" ]] || { echo "RTL missing: $rtl" >&2; exit 1; }
done

project_dir="$(mkdir -p "$(dirname "$project_dir")" && cd "$(dirname "$project_dir")" && pwd)/$(basename "$project_dir")"
rm -rf "$project_dir"

run() { echo "+ $*"; "$@"; }

run "$ecc" init "$project_dir" --plain

if [[ -n "$ecc_toml" ]]; then
  cp -f "$ecc_toml" "$project_dir/ecc.toml"
fi

mkdir -p "$project_dir/rtl"
for rtl in "${rtl_paths[@]}"; do
  cp -f "$rtl" "$project_dir/rtl/$(basename "$rtl")"
done

run "$ecc" pdk set-root "$pdk_root" --project "$project_dir" --plain
run "$ecc" run --project "$project_dir" --workspace "$workspace_name" --plain

workspace="$project_dir/$workspace_name"
marker="$(dirname "$project_dir")/eda-gcd.ok"
if [[ ! -f "$workspace/home/flow.json" ]]; then
  rm -f "$marker"
  echo "EDA rtl2gds failed → missing flow.json under $workspace" >&2
  exit 1
fi
printf '%s\n' "$workspace" >"$marker"
echo "EDA rtl2gds ok → $workspace"
echo "ECC_WORKSPACE=$workspace"
