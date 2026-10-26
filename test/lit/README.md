# Lit suites (CI contracts)

This tree holds **CI-side** lit suites and libraries. Product readiness remains
`ecc signoff inspect/export`. Ordinary CLI/RPC unit and subprocess coverage
lives under `test/cli` and `test/runtime` (pytest), not in this lit tree.

## Suites

| Suite | Path | Runner |
|-------|------|--------|
| Signoff CSV gates (library) | `csv_gates/` | used by designs repo / e2e via `nix run .#signoff-lit` |
| Project scenarios | `project/` | CLI `--project` Synthesis smoke |

## Project scenarios (`project/`)

One lit case + FileCheck contract (`checks/status_success.check`):

- **CLI** — `ecc run --project … --from/--to Synthesis` then `ecc status --project`

RPC stdio lifecycle / framing is covered by pytest (`test/runtime/test_stdio_server.py`),
not duplicated here.

Drivers live under `nix/scripts/`:

- `prepare_gcd_project.sh`
- `run_cli_project_scenario.sh`
- `ci_project_lit.sh` (CI entry; expects Nix on PATH — same Determinate install as other jobs)

### Local / CI run

```bash
export CHIPCOMPILER_ICS55_PDK_ROOT=/path/to/icsprout55-pdk
# OSS CAD / sizer env as for normal ecc run
bash nix/scripts/ci_project_lit.sh
# or:
nix run .#signoff-lit -- test/lit/project
```

Without `CHIPCOMPILER_ICS55_PDK_ROOT`, lit reports `UNSUPPORTED` (`REQUIRES: ics55-pdk`).

## Signoff CSV gates (`csv_gates/`)

Gates against **real design workspaces** from the PyInstaller e2e job;
profiles/FileCheck files for packaged designs live in
[openecos-projects/ecc-ci-designs](https://github.com/openecos-projects/ecc-ci-designs).

```bash
ECC_FLOW_WORKSPACES=<workspaces> \
  nix run .#signoff-lit -- <ecc-ci-designs checkout>
```

Status: **v0 / trial** — CI contract, not product signoff truth.
