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

## Status (2026-10-19 11:42 UTC)

Reported on this branch because later heartbeats were only written in chat.

Verified again at 2026-10-19 11:42 UTC:

- This branch tip was `b64f0d7`. Both Decision lines above were still empty.
- `origin/main` was `26ba389`.
- `uv sync` succeeded on 2026-10-16. `ecc-dreamplace` and `ecc-tools-bin` installed. Build stayed at `build.tool-args = ["-j1"]`.
- `ruff check chipcompiler/ test/` passed.
- `pytest test/`: 2134 passed, 1 failed, 6 errors. The failure is `test_help_keeps_styles_when_color_is_forced` under `NO_COLOR=1` and `TERM=dumb`. The same test passed after those variables were unset. The 6 errors are missing `/home/kernel_dev/works/pdk/icsprout55-pdk`.
- `ty check` exits 1. Counts are in section 1. CI does not run `ty`.
- Working tree still has many 644-to-755 mode changes. They are not part of this commit.
- `gh` is not installed and `~/.config/gh` is absent, so no pull request was opened. The branch is on `git@github.com:plitenh/ecc.git`, branch `proposal/supervisor-open-questions`.

No further code changes until a Decision commit lands. The three-day window ends 2026-10-19 12:37 UTC.
