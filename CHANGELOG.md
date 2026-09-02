# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
the axes in [roadmap/quality.md](roadmap/quality.md) (ADR-0006) — code is
SemVer 0.x pre-v1, and data snapshots, schema, and method versions are
recorded separately in manifests once the pipeline exists.

## [Unreleased]

### Changed

- tinycity: tract polygon corners are rounded to six decimals like every
  other fixture coordinate, so the spine stage's output read back from the
  GeoJSON snapshot equals the golden geometry exactly. Only
  `expected/tracts_spine.parquet` (content) and its `CHECKSUMS.txt` line
  changed; the raw snapshots are byte-identical (EP-4b).
- Delisting window in `docs/policies.md` is now two-tier: 7 days for standard
  requests, 72 hours for safety-motivated requests (owner decision,
  2026-09-02; resolves the EP-1 carry-over).
- OQ-A (City license confirmation) **closed**: the address used on
  2026-08-23 did not exist and the message bounced; the request was re-sent
  on 2026-09-02 to the contact the City's Open Data Program page lists, and
  CityGeo (Office of Innovation & Technology) replied the same day that no
  terms exist beyond the published open-data terms page and the data is
  shared for any use that benefits the community. `docs/DATA-LICENSES.md`
  and `roadmap/sources.md` now record the confirmed position; the caveat
  wording is retired, takedown readiness stays standing policy.
- Dependabot no longer opens PRs against the vendored `source material/`
  JKAN tree: `bundler` and `npm` entries with `open-pull-requests-limit: 0`
  added to `.github/dependabot.yml`; PRs #1–#4 closed and the seven open
  alerts for that path dismissed as "not used" (owner decision, 2026-09-02).
  The tree is reference material that is never built, executed, or
  modified, so the alerts describe no exposure.
- Roadmap status surface: `roadmap/README.md` now carries per-milestone
  work-packet tables (packet, size, depends-on, status) as the place packet
  and milestone status is tracked, mirroring the sibling repositories'
  owner-facing roadmaps while keeping this repo's `[ ]` / `[~]` /
  `[x] <commit>` convention and unpadded `EP-N` numbering. M0 is recorded
  done at `9bcb7b2` (both packets done; go/no-go met). `milestones.md`
  gains a Packets column and points to the tables.
- Packet sizing: one packet is one session from 2026-09-02 on. The only L
  packet, EP-4, is split at its engine/runner boundary into
  `EP-4a-manifest-engine.md` (zones, manifests, guards, quarantine,
  snapshot-level `verify`) and `EP-4b-stage-runner.md` (stages,
  fingerprints, resume/cancel, preflight, `run/status/verify --fixture`).
  A lettered-split convention (`EP-Na`, `EP-Nb`, …, number kept) is
  documented as the pickup remedy for the remaining M packets (EP-5–EP-8);
  new packets are never authored above one session. `_TEMPLATE.md` updated;
  EP-5's prerequisite, the data dictionary, and the fixture README now cite
  EP-4a/EP-4b.
- `roadmap/milestones.md` gains a "Refinement-gate carry-ins" section, and
  the roadmap README's reading order points to it: deferred obligations from
  earlier packets are applied when a later milestone's EP files are
  authored. First entry: the M5 reliability conventions (OQ-I) with the
  locked-decision text, baseline check, apply list, and regression guard.

### Added

- **EP-4b — stage runner: fingerprints, resume/cancel, preflight,
  `phillysim run/status/verify`** (Planning Baseline v1.0; completes M1):
  - `phillysim.stages`: the stage registry. A `Stage` declares inputs and
    outputs as data-root-relative paths plus JSON parameters; a `Pipeline`
    validates the wiring as a DAG (every input external under `raw/` or
    produced by an earlier stage; every output produced once). Cooperative
    `CancelToken` with checkpoints inside stages.
  - `phillysim.runner`: fingerprint = SHA-256 of the inputs' content digests
    plus the parameters, recorded per stage in `<data root>/pipeline_state.json`
    (shape in `docs/data-dictionary.md`); a stage is skipped while its
    fingerprint is unchanged and its outputs are intact. Outputs are written
    to `cache/staging/<stage>/` and installed by atomic rename, so a failed
    or cancelled stage never leaves a partial file in a zone; it is recorded
    as incomplete and the next run resumes from it. `status` (fresh / stale /
    missing / incomplete) and `verify_state` (state file vs. zones: outputs
    present and unaltered, no incomplete stage, no leftover staging, no
    unknown record). The raw zone stays immutable under the runner.
  - `phillysim.preflight`: free disk, physical RAM, Python version, the six
    locked packages, writable root; every check reported in one pass and any
    failure refuses the run. Real-run thresholds from architecture.md
    (≥150 GB free disk, 24 GB RAM); fixture-scale thresholds for `--fixture`,
    labelled as such. No new dependency (RAM via Win32 / `/proc/meminfo` /
    `sysconf`).
  - `phillysim.fixtures.pipeline`: the eleven fixture stages (`acquire`,
    `validate`, `spine`, `demographics`, `destinations`, `conflate`, `hours`,
    `network`, `travel_times`, `metrics`, `publish`) carrying tinycity from
    generated raw snapshots (admitted through the EP-4a guards) to the
    expected tables; `hours` and `travel_times` are explicit stubs fed by the
    generator's oracle until M4 / M3; `publish` writes a plain CSV until
    EP-7 adds license bucketing. The four curated outputs equal the golden
    tables by content.
  - CLI: `phillysim run [--fixture] [--data-root DIR] [--stage NAME]
    [--param stage.key=value]`, `phillysim status [--fixture]`, and
    `phillysim verify` extended with stage-state coherence; `--fixture` now
    targets the fixture pipeline's own data root, `<data root>/fixture/`
    (gitignored, as is the state file).
  - CI runs `phillysim run --fixture`, `status --fixture`, and
    `verify --fixture` on Windows and Linux: the M1 go/no-go criterion.
  - Tests: 33 new (240 total): runner unit tests (registry rules,
    content-hash fingerprints, skip / rerun-only-dependents / resume after an
    injected failure / cancel at a checkpoint and between stages / immutable
    raw / no absolute paths in the state file), preflight negative tests with
    injected probes, and the integration suite on tinycity via the CLI.

- **EP-4a — manifest/snapshot engine, zones, download guards, quarantine**
  (Planning Baseline v1.0):
  - `phillysim.zones`: source-name and snapshot-ID rules (`YYYY-MM-DD`,
    `-N` same-day sequence), snapshot listing, stray-entry detection, and
    the one function that creates the zone layout (resolution still never
    does).
  - `phillysim.manifest`: the snapshot manifest as an owned model with every
    field rule enforced (UTC timestamp, http(s) URL without credentials,
    license bucket A/B, integer schema version, bare file names, 64-hex
    digests, terms archive listed), a canonical reader/writer that
    round-trips byte-for-byte, and `verify_snapshot` / `verify_raw_zone`
    naming every missing, altered, unlisted, or relocated file.
  - `phillysim.guards`: domain allowlist (https only, subdomain match, no
    IP literals or credentials), size cap before and during streaming,
    zip-slip path normalization (absolute paths, drive letters, `..`,
    symlink members), decompression-bomb ceilings (declared size, ratio,
    member count, actual bytes), plus guarded zip / gzip extraction. No
    adapter knowledge; allowlist and limits are always passed in.
  - `phillysim.quarantine`: default-deny `admit` (manifest → guards →
    checksums); any failure moves the whole snapshot to
    `data/quarantine/<source>/` and writes a reason file beside it.
  - `phillysim verify [--fixture | --raw DIR]`: snapshot-level verification
    with a per-snapshot report and non-zero exit on any failure.
  - Tests: 131 new (207 total) including one crafted negative input per
    guard, each shown to be refused *and* quarantined; a tampered byte in a
    fixture file fails `verify` naming the file; every manifest field shown
    required and every malformed form rejected.
  - The tinycity generator now builds its manifests through the engine; the
    committed fixture was regenerated for both variants and did not change
    by a byte (the "proposed" shape is now the owned shape, schema version
    still 1). Data dictionary manifest section promoted to owned and a
    quarantine reason-file section added.
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
