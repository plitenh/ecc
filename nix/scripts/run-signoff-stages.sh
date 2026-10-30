#!/usr/bin/env bash
# Run signoff stages as separate CI step boundaries.
#
# Sequence:
#   prepare -> impl -> harden -> lec -> physical -> sta -> ir_em
#
# For rtl2gds designs, prepare copies the project and the first implementation
# stage creates a full synthesis..Harden flow target, rehydrates the Yosys RTL
# filelist, then executes only synthesis..filler. Later stages run bounded
# ranges on the same full target, so a failure stops the job before the next
# stage.
#
# Non-rtl2gds presets (for example syn_sta) keep their configured preset and
# skip signoff stages that are not present in their persisted flow.
set -euo pipefail

usage() { sed -n '2,24p' "$0"; exit 2; }

ecc=""
designs_dir=""
design=""
out_root=""
pdk_root=""
stage=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ecc) ecc="${2:?}"; shift 2 ;;
    --designs-dir) designs_dir="${2:?}"; shift 2 ;;
    --design) design="${2:?}"; shift 2 ;;
    --out-root) out_root="${2:?}"; shift 2 ;;
    --pdk-root) pdk_root="${2:?}"; shift 2 ;;
    --stage) stage="${2:?}"; shift 2 ;;
    -h | --help) usage ;;
    *) echo "unknown arg: $1" >&2; usage ;;
  esac
done

[[ -n "$ecc" && -x "$ecc" ]] || { echo "error: --ecc must be an executable ecc binary" >&2; exit 2; }
[[ -n "$designs_dir" && -d "$designs_dir" ]] || { echo "error: --designs-dir must be a directory" >&2; exit 2; }
[[ -n "$design" ]] || { echo "error: --design is required" >&2; exit 2; }
[[ -n "$stage" ]] || { echo "error: --stage is required" >&2; exit 2; }

out_root="${out_root:-ci-artifacts/e2e}"
mkdir -p "$out_root"
out_root="$(cd "$out_root" && pwd)"
designs_dir="$(cd "$designs_dir" && pwd)"
ecc="$(cd "$(dirname "$ecc")" && pwd)/$(basename "$ecc")"

if [[ -z "$pdk_root" ]]; then
  pdk_root="${CHIPCOMPILER_ICS55_PDK_ROOT:-}"
fi
if [[ -z "$pdk_root" ]]; then
  for candidate in "$PWD/../pdk/icsprout55-pdk" "${ECC_REPO_ROOT:-$PWD}/../pdk/icsprout55-pdk"; do
    [[ -d "$candidate" ]] && pdk_root="$(cd "$candidate" && pwd)" && break
  done
fi
[[ -n "$pdk_root" && -d "$pdk_root" ]] || {
  echo "error: PDK root not found; pass --pdk-root or set CHIPCOMPILER_ICS55_PDK_ROOT" >&2
  exit 1
}

src="$designs_dir/$design"
dst="$out_root/$design"
log="$out_root/$design-$stage.log"

run_ecc() {
  local label="$1"
  shift
  local current_log="$out_root/$design-$label.log"
  echo "running $label: $*"
  if CHIPCOMPILER_ICS55_PDK_ROOT="$pdk_root" PYTHONUNBUFFERED=1 \
    "$ecc" "$@" 2>&1 | tee "$current_log"; then
    return 0
  fi
  echo "FAIL $design $label (log: $current_log)" >&2
  return 1
}

project_preset() {
  python3 - "$1/ecc.toml" <<'PY'
import sys
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

with open(sys.argv[1], "rb") as stream:
    data = tomllib.load(stream)
flow = data.get("flow", {})
print(flow.get("preset", "rtl2gds"))
PY
}

flow_has_step() {
  local workspace="$1"
  local wanted="$2"
  local flow_json="$workspace/home/flow.json"
  [[ -f "$flow_json" ]] || return 1
  python3 - "$flow_json" "$wanted" <<'PY'
import json
import sys

flow = json.load(open(sys.argv[1], encoding="utf-8"))
wanted = sys.argv[2].lower()
for step in flow.get("steps", []):
    if str(step.get("name", "")).lower() == wanted:
        sys.exit(0)
sys.exit(1)
PY
}

ensure_rtl_filelist() {
  local project="$1"
  local workspace="$2"
  local origin="$workspace/origin"
  local filelist="$origin/filelist"
  mkdir -p "$origin"
  if [[ -s "$filelist" ]]; then
    echo "using existing RTL filelist $filelist"
    return 0
  fi
  python3 - "$project" "$filelist" <<'PY'
from pathlib import Path
import sys

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

project = Path(sys.argv[1])
filelist = Path(sys.argv[2])
with (project / "ecc.toml").open("rb") as stream:
    data = tomllib.load(stream)
rtl = data.get("design", {}).get("rtl", [])
paths = []
for entry in rtl:
    candidate = (project / entry).resolve()
    if not candidate.is_file():
        raise SystemExit(f"RTL source not found: {candidate}")
    paths.append(str(candidate))
filelist.write_text("\n".join(paths) + "\n", encoding="utf-8")
print(f"wrote RTL filelist {filelist}")
PY
}

create_full_rtl2gds_target() {
  run_ecc prepare-full workspace create default \
    --project "$dst" \
    --from synthesis \
    --to Harden \
    --plain
  ensure_rtl_filelist "$dst" "$dst/default"
  run_ecc hydrate-filelist param set file_list "$dst/default/origin/filelist" \
    --project "$dst" \
    --workspace default
}

run_if_present() {
  local label="$1"
  local step="$2"
  shift 2
  if ! flow_has_step "$dst/default" "$step"; then
    echo "SKIP $design $label (step $step not in persisted flow)"
    return 0
  fi
  run_ecc "$label" "$@"
}

case "$stage" in
  prepare)
    if [[ ! -f "$src/ecc.toml" ]]; then
      echo "FAIL $design prepare (missing $src/ecc.toml)" >&2
      exit 1
    fi
    rm -rf "$dst"
    mkdir -p "$out_root"
    cp -a "$src" "$dst"
    echo "prepared $design in $dst"
    ;;
  impl)
    if [[ "$(project_preset "$dst")" != "rtl2gds" ]]; then
      run_ecc impl run --project "$dst" --workspace default --plain
    else
      if [[ ! -f "$dst/default/home/flow.json" ]]; then
        create_full_rtl2gds_target
      fi
      run_ecc impl run --project "$dst" --workspace default --from synthesis --to filler --plain
    fi
    ;;
  harden)
    run_if_present harden Harden run --project "$dst" --workspace default --from Harden --to Harden --plain
    ;;
  lec)
    run_if_present lec postRouteLec run --project "$dst" --workspace default --from postRouteLec --to postRouteLec --plain
    ;;
  physical)
    run_if_present physical lvs run --project "$dst" --workspace default --from lvs --to antennaCheck --plain
    ;;
  sta)
    run_if_present sta sta run --project "$dst" --workspace default --from rcx --to sta --plain
    ;;
  ir_em)
    run_if_present ir_em emir run --project "$dst" --workspace default --from powerAnalysis --to emir --plain
    ;;
  *)
    echo "unknown stage: $stage" >&2
    usage
    ;;
esac
