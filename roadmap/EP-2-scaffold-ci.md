# EP-2 — Python scaffold + offline CI skeleton

**Status:** [x] 9bcb7b2 · **Milestone:** M0 · **Effort:** M (1–2 sessions, high confidence) · **Parallel with:** —

## Outcome & value
A `uv`-managed package `phillysim` under `phillysim/` with pinned Python
3.12+, Typer CLI entry (`phillysim --help` works), config module (app-owned
`data/` root; no absolute paths), pre-commit (format/lint), and a GitHub
Actions workflow: SHA-pinned actions, minimal permissions, fully offline,
running lint + a placeholder test. Secret scanning, push protection, and
Dependabot enabled (owner clicks documented in handoff).

## Scope
- in: scaffold, CLI entry, config, pre-commit, CI workflow, dependency-policy
  test.
- out (explicit non-scope): any pipeline logic; fixtures (EP-3).

## Prerequisites & locked decisions
- prerequisites: EP-1.
- locked decisions honored: ADR-0001 (stack; GDAL/fiona PyPI ban enforced via
  a dependency-check test); B3-07 CLI shape (plain Typer-style stages).
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: lockfile committed; no network
access in CI.

## Likely components & contracts (proposed)
`phillysim/pyproject.toml`; `phillysim/src/phillysim/{__init__,cli,config}.py`;
`.pre-commit-config.yaml`; `.github/workflows/ci.yml`;
`tests/test_smoke.py`; `tests/test_dependency_policy.py` (asserts banned
packages absent from the resolved tree).

## Implementation notes
Windows-native is primary: every pinned dependency must install from wheels
on Windows py3.12+. Config resolves the `data/` root relative to the repo or
an env override — never a hard-coded absolute path.

## Acceptance criteria & evidence
- [x] Fresh clone → documented setup commands → CLI help + tests green
  locally and in CI. — Locally via a fresh extraction of the tracked files
  into a scratch directory (`uv sync --locked`, `phillysim --help`,
  24 tests green); in CI via run 33655714859 (below).
- [x] Dependency-policy test fails if `GDAL` or `fiona` enters the tree
  (negative check verified once deliberately). — The negative check is
  built in: parametrized tests feed lockfile and pyproject text containing
  `fiona`/`GDAL` (all casings) to the detector and require it to fire, so
  it is verified on every run rather than once.
- Evidence: green CI run; setup section in README.

## Tests / validation
`uv run pytest`; CI run green.

## Resource budget
Trivial.

## Risks, rollback, stop condition
Windows wheel failure for any pinned dependency → stop, record evidence,
resolve versions before proceeding; do not swap stack unilaterally.

## Documentation / ADR updates
README setup section; ADR-0001 committed to `roadmap/adr/` already — link it
from code docs if a docs stub exists.

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-2 — done at commit `9bcb7b2` (+ this status commit).
  Planning Baseline v1.0. CI run
  [33655714859](https://github.com/willtfarrington/phillysim/actions/runs/33655714859)
  green on `windows-latest` and `ubuntu-latest`.
- **Files changed:** `phillysim/pyproject.toml`, `phillysim/uv.lock`,
  `phillysim/.python-version`, `phillysim/README.md` (replaces the empty
  placeholder), `phillysim/src/phillysim/{__init__,cli,config}.py`,
  `phillysim/tests/{test_smoke,test_config,test_dependency_policy}.py`,
  `.pre-commit-config.yaml`, `.github/workflows/ci.yml`,
  `.github/dependabot.yml`; setup sections in `README.md` and
  `CONTRIBUTING.md`; `CHANGELOG.md` entry; this file.
- **Commands/tests run + results:** `uv sync` (CPython 3.13.15 managed by
  uv; 36 packages, every one from a wheel on Windows); `uv sync --locked`
  clean; `uv run pytest` → 24 passed; `uv run ruff check .` and
  `ruff format --check .` clean; `pre-commit install` + `pre-commit run
  --all-files` all hooks passed with no file modified; `phillysim --help`,
  `version`, `paths`, `paths --json` (with env override) behave as
  documented; fresh-extract simulation of a clone green; scan of the tree for
  absolute paths, usernames, and the hostname → none; CI run above green.
- **Resource observations:** trivial, as budgeted. Single session. Sync and
  tests run in seconds; each CI job completes in well under a minute.
- **Decisions made (revisable, below ADR level):**
  - Locked geo stack (geopandas, pyogrio, shapely, pyproj, duckdb, pyarrow)
    declared as runtime dependencies now so the ban test and the Windows-wheel
    requirement bite from the first commit; r5py + pinned JDK deferred to M3.
    Owner confirmed interactively.
  - CPython pinned to **3.13** in `.python-version` (no 3.12 on the machine;
    uv manages 3.13; the system 3.14 is never used); `requires-python >=3.12`.
  - Layout follows the sibling-repo convention: `<repo>/phillysim/` is the uv
    project (pyproject, src, tests); pre-commit config and `.github/` sit at
    the repo root. Build backend is hatchling (avoids coupling to the uv
    version).
  - CI matrix runs Windows **and** Linux; Linux stands in as evidence for the
    documented WSL2 fallback. "Fully offline" is interpreted and documented in
    the workflow header as: no data-source calls, no secrets; CI reaches only
    GitHub and PyPI (strictly from the committed lockfile).
  - Dependabot covers the `uv` and `github-actions` ecosystems on a monthly
    cadence (within governance.md's roughly-quarterly review).
  - Data-root resolution: `PHILLYSIM_DATA_ROOT` → nearest ancestor with a
    `.git` entry `/data` → `<cwd>/data`; zones are raw, intermediate, curated,
    public, plus quarantine and cache. Resolution never creates directories.
  - The negative dependency-policy check is permanent (parametrized) rather
    than a one-off manual verification.
- **Owner decisions taken interactively (2026-09-02):** commit and push
  (yes); enable repo security via API (yes — secret scanning, push
  protection, vulnerability alerts, Dependabot security updates, and private
  vulnerability reporting all enabled and verified by reading the settings
  back); update the GitHub repo description to the EP-1 suggested text (yes —
  done, closes that EP-1 carry-over); keep the geo stack (yes).
- **Process note:** the owner's global session rules now require every work
  packet to end with an interactive review of open issues and owner-level
  decisions before it is called complete; this packet was the first run
  under that rule.
- **Unresolved risks/questions:** EP-1 carry-overs still open: send the
  opendata@phila.gov license-confirmation draft (OQ-A); confirm the 7-day
  delisting window. Dependabot version-update PRs will begin arriving
  monthly and need owner triage. Secret-scanning non-provider patterns and
  validity checks were left disabled (no document assumes them).
- **No-go areas touched:** none — no source data, no pipeline logic,
  `source material/` untouched and excluded from every hook, no machine
  identifiers or absolute paths in tracked files (scanned), no outbound calls
  beyond GitHub (push, repo-settings API) and PyPI (locked sync).
- **Exact next packet:** EP-3 (tinycity synthetic fixture).
