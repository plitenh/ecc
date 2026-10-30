#!/usr/bin/env bash
# Run signoff stages as separate CI step boundaries.
#
# Sequence:
#   prepare -> impl -> harden -> lec -> physical -> sta -> ir_em
#
# prepare copies the design and creates a full synthesis..Harden flow
# workspace without running it. Each later stage runs a bounded range on the
# same workspace so a failure stops the job before the next stage.
set -euo pipefail

usage() { sed -n '2,20p' "$0"; exit 2; }

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

case "$stage" in
  prepare)
    rm -rf "$dst"
    mkdir -p "$out_root"
    cp -a "$src" "$dst"
    run_ecc prepare workspace create default \
      --project "$dst" \
      --from synthesis \
      --to Harden \
      --plain
    ;;
  impl)
    run_ecc impl run --project "$dst" --workspace default --from synthesis --to filler --plain
    ;;
  harden)
    run_ecc harden run --project "$dst" --workspace default --from Harden --to Harden --plain
    ;;
  lec)
    run_ecc lec run --project "$dst" --workspace default --from postRouteLec --to postRouteLec --plain
    ;;
  physical)
    run_ecc physical run --project "$dst" --workspace default --from lvs --to antennaCheck --plain
    ;;
  sta)
    run_ecc sta run --project "$dst" --workspace default --from rcx --to sta --plain
    ;;
  ir_em)
    run_ecc ir_em run --project "$dst" --workspace default --from powerAnalysis --to emir --plain
    ;;
  *)
    echo "unknown stage: $stage" >&2
    usage
    ;;
esac
