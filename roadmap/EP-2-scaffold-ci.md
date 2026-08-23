# EP-2 — Python scaffold + offline CI skeleton

**Status:** [ ] planned · **Milestone:** M0 · **Effort:** M (1–2 sessions, high confidence) · **Parallel with:** —

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
- [ ] Fresh clone → documented setup commands → CLI help + tests green
  locally and in CI.
- [ ] Dependency-policy test fails if `GDAL` or `fiona` enters the tree
  (negative check verified once deliberately).
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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- exact next packet: EP-3
