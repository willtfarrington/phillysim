# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
the axes in [roadmap/quality.md](roadmap/quality.md) (ADR-0006) — code is
SemVer 0.x pre-v1, and data snapshots, schema, and method versions are
recorded separately in manifests once the pipeline exists.

## [Unreleased]

### Changed

- Delisting window in `docs/policies.md` is now two-tier: 7 days for standard
  requests, 72 hours for safety-motivated requests (owner decision,
  2026-09-02; resolves the EP-1 carry-over).
- OQ-A (City license confirmation): the address used on 2026-08-23 did not
  exist and the message bounced; the request is being re-sent to the
  contact the City's Open Data Program page actually lists
  (`roadmap/open-questions.md`).
- Dependabot no longer opens PRs against the vendored `source material/`
  JKAN tree: `bundler` and `npm` entries with `open-pull-requests-limit: 0`
  added to `.github/dependabot.yml`; PRs #1–#4 closed and the seven open
  alerts for that path dismissed as "not used" (owner decision, 2026-09-02).
  The tree is reference material that is never built, executed, or
  modified, so the alerts describe no exposure.

### Added

- **EP-3 — tinycity synthetic fixture + source-contract harness** (Planning
  Baseline v1.0):
  - `phillysim gen-tinycity`: deterministic generator for a wholly synthetic
    mini-geography (six fake tracts in the open Atlantic, thirteen destination
    points across all three v1 categories, fake ACS with margins of error
    covering all three CV tiers, tiny GTFS and street-network stubs, a
    precomputed travel-time matrix standing in for routing until M3, and
    golden expected tables). Committed under
    `phillysim/tests/fixtures/tinycity/` with `CHECKSUMS.txt`; an
    `--variant invalid` copy with eight injected faults under
    `tinycity-invalid/`.
  - Hours edge cases from methodology.md Tier 2 (weekend-only, seasonal,
    missing, malformed) with hand-derived open/closed answers for the pinned
    analysis weeks.
  - `phillysim.contracts`: adapter-agnostic source-contract harness (schema,
    key, row-count, license bucket + schema version, geometry type / CRS /
    validity / bounds) and the locked analytic-table contract
    `{estimate, moe, cv_tier, reliability_action}`.
  - Tests: two-run byte determinism, committed-fixture currency, harness
    negative tests for every check kind, every injected fault caught.
  - `docs/data-dictionary.md` seeded at schema version 1.
- **EP-2 — Python scaffold + offline CI skeleton** (Planning Baseline v1.0):
  - `phillysim/` uv project: `pyproject.toml` declaring the locked stack
    (typer, geopandas, pyogrio, shapely, pyproj, duckdb, pyarrow), committed
    `uv.lock`, CPython pinned to 3.13 (`>=3.12` declared). Every dependency
    installs from wheels on Windows.
  - Typer CLI entry point: `phillysim --help`, `version`, `paths`.
  - Config module resolving the app-owned `data/` root (env override, then
    repo root, then working directory); no absolute paths anywhere.
  - Tests: smoke, config, and dependency policy (GDAL/fiona ban, ADR-0001,
    with built-in negative checks so the guard is proven on every run).
  - `.pre-commit-config.yaml` (ruff via uv; pre-commit-hooks v6.0.0).
  - `.github/workflows/ci.yml` (SHA-pinned actions, read-only token,
    Windows + Linux matrix, fixtures only) and `.github/dependabot.yml`
    (uv + GitHub Actions ecosystems, monthly).
  - Package README with setup commands; setup sections in the root README
    and CONTRIBUTING.
- **EP-1 — repository governance bootstrap** (Planning Baseline v1.0):
  - README rewritten to the charter framing: measuring access, not modeling
    outcomes; the "sim" name explained; AI disclosure; non-endorsement.
  - `.gitignore` covering data zones, secrets, caches, logs, notebook
    checkpoints, and local databases.
  - `docs/CLAIMS.md` — claims matrix instantiated verbatim from charter.md.
  - `docs/DATA-LICENSES.md` — pre-acquisition stub: City-license caveat,
    ODbL/CC BY output buckets (ADR-0003), source terms summary.
  - `docs/policies.md` — correction channel and delisting/takedown policy.
  - `CONTRIBUTING.md` and `SECURITY.md`.
  - This changelog.

### Earlier

- Planning Baseline v1.0 accepted; roadmap package added (`roadmap/`:
  charter, scope, sources, methodology, architecture, governance, quality,
  milestones, packets EP-1..EP-8, ADRs 0001–0006).
- MIT license added; OpenDataPhilly JKAN tree vendored under
  `source material/` for reference, provenance documented.
