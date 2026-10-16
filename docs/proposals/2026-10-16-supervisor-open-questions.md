# Supervisor open questions (2026-10-16)

Answer by editing the "Decision" lines and committing on this branch.
Until those commits land, the supervisor will not expand into the work below.

## 1. `ty check` scope

Current state (verified 2026-10-16):

- `uv run ty check` exits 1.
- About 234 diagnostics point at `chipcompiler/` (argument types, deprecated calls, missing attributes, return types).
- About 1100 more point at `chipcompiler/thirdparty/` and installed packages.
- `.github/workflows/ci.yml` runs pytest and ruff. It does not run `ty`.
- `[tool.ty] src.include` lists `chipcompiler/**/*.py` and `tests/**/*.py`. The test tree is `test/`.

Options:

- A. Leave `ty` as a local signal. Do not mass-edit annotations in this window.
- B. Make `ty` a CI gate for `chipcompiler/` and `test/` only, and fix the existing diagnostics first.
- C. Make `ty` a CI gate, but only for new code, with a checked-in baseline of the current diagnostics.

Recommendation: A for this three-day window. B is a separate change with its own review.

Decision:

## 2. ecc-dreamplace gitlink

Current state (verified 2026-10-16):

- Parent repo pins `chipcompiler/thirdparty/ecc-dreamplace` at `308dcd35`.
- The checkout is branch `parallel_build` at `f7bdecf`, plus a local `pyproject.toml` edit.
- That edit keeps the serial build limit on the existing scikit-build table: `build.tool-args = ["-j1"]`.
- A second `[tool.scikit-build.build]` table was invalid TOML (duplicate key) and blocked `uv sync`. The limit now lives on the existing `build` table so `-j1` still applies.

Options:

- A. Keep the parent pin. Do not commit the submodule branch move from this supervisor.
- B. Move the parent gitlink to the `parallel_build` commit after the `-j1` change is committed in ecc-dreamplace.

Recommendation: A until the `-j1` change is committed in the dreamplace repo.

Decision:
