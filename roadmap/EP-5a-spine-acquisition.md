# EP-5a — Spine source adapters: acquisition path + TIGER/CenPop/ACS snapshots

**Status:** [x] 39a6828 (done 2026-09-02) · **Milestone:** M2 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-5 (2026-09-02, EP-9 pre-read; EP-5b is the other half)

## Outcome & value
The project's first real acquisition path and its first real snapshots. A
guarded download function turns EP-4a's local primitives into the outbound
path architecture.md's security section describes (domain allowlist first,
https only, timeouts and backoff, capped streaming through `copy_capped`,
the zip / gzip guards, the terms page in force archived beside the data,
a manifest built through `phillysim.manifest`, admission only through
`quarantine.admit`). Three adapters use it: TIGER/Line 2025 census tracts,
CenPop2020 population-weighted tract centroids, and ACS 5-year 2020–2024
selected tables with margins of error. Each produces an immutable,
manifest-recorded snapshot in the raw zone, has a source contract, and has
a fixture-scale, real-shaped sample committed for offline CI. The first real
pipeline is registered so that `phillysim run --stage validate` works
without `--fixture`. After this packet, EP-5b builds the curated spine on
these snapshots.

## Scope
- in:
  1. Download module: allowlist check → https-only fetch with timeout and
     bounded backoff → `copy_capped` streaming under per-source `Limits`
     → archive guards → terms-page archive → manifest → `admit`. Dual-URL
     (`acquisition_url_alt`) supported. No default allowlist: each adapter
     declares its domains.
  2. Three adapters (`tiger`, `cenpop`, `acs`) producing snapshots
     `raw/tiger_tracts/<id>/`, `raw/cenpop/<id>/`, `raw/acs/<id>/` (source
     names as the fixture already uses them), with the county / bounding-box
     filter applied at ingest per architecture.md's early-filtering rule;
     the packet records, per source, whether the raw file is stored as
     delivered (state-level TIGER and CenPop files, verifiable against the
     provider) and filtered at first read, or requested county-scoped (ACS
     API), and why.
  3. A `SourceContract` per source (schema, key, license bucket A, schema
     version, geometry for TIGER) and a small committed sample per source,
     real-shaped and US public domain, documented as such in its README,
     for the contract tests to run offline in CI.
  4. The real pipeline registered in `phillysim.cli._pipeline(fixture=False)`
     with the `acquire` and `validate` stages for these three sources, so
     that `run`, `status`, and `verify` work on the real data root; the
     packet decides and documents how real stages coexist with the fixture
     pipeline's identical stage names (separate roots today).
  5. EP-4a's placeholder guard `Limits` confirmed per source and recorded.
- out (explicit non-scope): the curated spine, invariant tests, the
  analysis-CRS ADR, data cards (EP-5b); ACS-derived metrics (EP-7);
  destination sources (EP-6); any retry policy beyond bounded backoff; a
  Census API key requirement (none in CI; optional locally if the API
  demands it, read from the environment, never committed).

## Prerequisites & locked decisions
- prerequisites: EP-9 (checkpoint), EP-4b (and therefore EP-4a).
- locked decisions honored: 2020 tracts; pinned vintages (sources.md: TIGER/
  Line 2025, CenPop2020, ACS 5-year 2020–2024); the ACS variable list is
  what methodology.md names, and anything more is a methods-version bump
  (ADR-0006); ADR-0003 buckets (all three sources Bucket A); the manifest
  field rules of docs/data-dictionary.md; the outbound domain allowlist and
  timeout/backoff rules of architecture.md "Security".
- dependencies: Census / TIGER endpoints (`www2.census.gov`,
  `api.census.gov`, and whichever host serves CenPop2020; every host
  declared in the adapter's allowlist and recorded in the handoff).

## Safety preconditions
Standing policy (see EP-1). Packet-specific: Census terms honored and the
terms page in force archived with each snapshot; snapshots stay in the
gitignored raw zone; only fixture-scale samples become CI fixtures, and only
with their US-public-domain status documented; CI stays offline (contract
tests run on the committed samples; the real run is manual and recorded in
the handoff); no secret in the repository or CI; no PHI exists in these
sources.

## Likely components & contracts (proposed)
`src/phillysim/download.py` (guarded fetch); `src/phillysim/adapters/
{__init__,tiger,cenpop,acs}.py`; `src/phillysim/pipeline.py` (the real
pipeline registration; name proposed); `tests/contracts/test_spine_sources.py`;
`tests/test_download.py` (crafted local inputs only, no network);
`tests/fixtures/spine-samples/` with a README; `docs/data-dictionary.md`
raw-source sections for the three real sources; `docs/DATA-LICENSES.md`
dated entries for the three sources.

## Implementation notes
Order of checks in the download path is fixed: allowlist before any
connection, cap during streaming, guards before extraction, digests before
admission. Snapshot IDs come from `zones.next_snapshot_id`; the raw zone is
never overwritten. The archived terms page is a file in the snapshot named
by `terms_archive`. Stage names stay those of the fixture pipeline so the
architecture.md stage table holds for both. Keep the real run's console
output (counts, sizes, timings) for the handoff.

## Acceptance criteria & evidence
- [x] From a fresh clone, a manual `phillysim run --stage validate`
      acquires the three snapshots, admits them, and `phillysim verify`
      passes on the real data root (counts, sizes, and timings recorded).
      Done 2026-09-02, fresh clone of `39a6828` (handoff below).
- [x] Every manifest carries `terms_archive`, `license_bucket = "A"`, and a
      `license_note`; the archived terms page is present and checksummed.
      Enforced by the manifest engine and asserted by the contract and
      integration suites on the samples.
- [x] Contract tests for the three sources green in CI on the committed
      samples; `uv run pytest` green; no test reaches the network (the
      suite now disables sockets, `tests/conftest.py`). CI run 33697076059.
- [x] Guard `Limits` confirmed per source and recorded in the handoff.
- Evidence: CI run green on Windows + Linux; the real run documented in the
  handoff.

## Tests / validation
`uv run pytest` (contracts on samples; download path on crafted local
inputs); the manual real run above.

## Resource budget
Network: a few hundred MB at most (state-level TIGER tracts, CenPop CSV, a
county-scoped ACS request). Disk: <2 GB. Runtime: minutes.

## Risks, rollback, stop condition
Endpoint URL drift → dual-URL field; record and continue. ACS API rate
limit or key requirement → document; never commit a key. **Stop** if a
terms page is unreachable or its text differs from what sources.md records
(surface to the owner; do not acquire). Rollback: snapshots are gitignored;
code reverts cleanly.

## Documentation / ADR updates
Data dictionary (three raw-source sections); DATA-LICENSES dated entries;
`phillysim/README.md` (download path, real pipeline); CHANGELOG; packet row
in `roadmap/README.md`. No ADR (the CRS ADR belongs to EP-5b).

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-5a — done at commit `39a6828` (+ this status commit).
  Planning Baseline v1.0. CI run
  [33697076059](https://github.com/willtfarrington/phillysim/actions/runs/33697076059)
  on `39a6828` green on `windows-latest` and `ubuntu-latest` (pytest,
  ruff, and the three fixture-pipeline steps; CI never runs the real
  pipeline).
- **Files changed:** new `phillysim/src/phillysim/download.py`,
  `phillysim/src/phillysim/adapters/{__init__,base,tiger,cenpop,acs}.py`,
  `phillysim/src/phillysim/pipeline.py`; `cli.py` (real pipeline behind
  `run` / `status` / `verify`, download log on stdout, "not registered"
  branches removed); `runner.py` (two fixes below); new
  `tests/test_download.py`, `tests/contracts/test_spine_sources.py`,
  `tests/integration/test_real_pipeline.py`,
  `tests/fixtures/spine-samples/` (README, `build_samples.py`, three sample
  snapshots); `tests/conftest.py` (no-network guard, samples fixture);
  `tests/test_runner.py` and `tests/integration/test_fixture_pipeline.py`
  (updated expectations); `docs/data-dictionary.md` (three raw-source
  sections, `terms` reason kind, `synthetic` wording, `acquisition.json`
  row); `docs/DATA-LICENSES.md` (status, three dated snapshot records,
  summary rows); `phillysim/README.md` (layout, "The real pipeline and the
  download path", first-real-run numbers); root `README.md` (status);
  `roadmap/architecture.md` (stage rows 1–2); `roadmap/quality.md` (test
  matrix row); `CHANGELOG.md`; `roadmap/README.md` (packet row); this file.
- **Commands/tests run + results.** Working clone: `uv run pytest` → 301
  passed (240 before; 61 new) in about 8 s; `ruff check` / `ruff format
  --check` clean; `pre-commit run --all-files` all hooks passed; staged
  diff scanned for usernames / absolute paths → none. **Real run, working
  clone (`data/`, resolved from the repo root):** first `phillysim run
  --stage validate` fetched everything (below) but failed installing the
  TIGER snapshot with `PermissionError: [WinError 5]` on the atomic rename
  (a scanner holding the just-written 13 MB zip); the resumed run re-used
  the two admitted snapshots, re-fetched TIGER, and completed; a third run
  skipped both stages (1.1 s); `status` 2 fresh (1.0 s); `verify` 3 of 3
  snapshots, 2 of 2 stages (1.1 s). That failure produced the two runner
  fixes and a test each. **Fresh-clone rehearsal of `39a6828`** (scratch
  directory, `git clone -c core.longpaths=true`, deleted afterwards):
  clone 0.7 s; `uv sync --locked` 6.6 s; `uv run pytest` 301 passed in
  21 s (cold caches); `phillysim run --stage validate` 6.9 s wall
  (preflight passed on the real thresholds; `acquire` 4.7 s: ACS B01003
  18,313,708 bytes in 0.6 s, B08201 65,043,091 bytes in 1.2 s, CenPop
  144,662 bytes in 0.2 s, TIGER 13,109,450 bytes in 0.5 s, terms page
  311,057 bytes in 0.5–0.6 s × 3, every fetch one attempt; `validate`
  1.1 s); second run 0 ran / 2 skipped in 1.2 s; `status` 2 fresh, 0
  stale, 0 missing, 0 incomplete; `verify` 3 of 3 snapshots verified, 2 of
  2 stages done and intact, exit 0; `git status` clean (data root
  gitignored). `validation.json`: 408 rows per source, no nulls in any
  contract column, no violations. Data-file digests are identical across
  the two clones (the provider's bytes are reproducible):
  `tl_2025_42_tract.zip` `818bdadf…86d196`, `CenPop2020_Mean_TR42.txt`
  `c5c3feea…53ec5e`, `acsdt5y2024-b01003.dat` `38d1a992…b6ca90`,
  `acsdt5y2024-b08201.dat` `2f64e698…df6b4d` (full digests in the
  manifests). The archived terms page is **not** byte-stable across
  fetches (the Census page embeds per-response content), so its digest is
  per snapshot; the checked sentence is what is stable.
- **Resource observations:** network 97 MB per fresh acquisition (well
  under "a few hundred MB"); raw zone 94 MB (ACS 80 MB, TIGER 13 MB,
  CenPop 0.5 MB; under 2 GB); runtime seconds. One session. Confirmed
  guard `Limits` per source (recorded in `acquisition.json` too):
  `tiger_tracts` 64 MiB file / 512 MiB extracted / ratio 50 / 20 members
  (actual: 13.1 MB zip, seven members, well under); `cenpop` 16 MiB / 16
  MiB / 50 / 1 (actual 145 KB); `acs` 256 MiB / 256 MiB / 50 / 1 (actual
  65 MB largest). EP-4a's placeholder defaults (4 GB / 16 GB / 200:1 /
  10k) are not used by any real source.
- **Decisions made (owner-reviewed 2026-09-02, all recommended options
  accepted):**
  - **ACS source path:** the Census data API redirected every key-less
    request to `missing_key.html` on 2026-09-02, so ACS is acquired from
    the key-free table-based summary file on `www2.census.gov`
    (`acsdt5y2024-b01003.dat`, `acsdt5y2024-b08201.dat`, nationwide,
    stored as delivered). No secret exists in the project; the download
    path keeps a never-recorded `query_secret` hook should the API ever be
    needed. The API Terms of Service and their attribution notice are not
    engaged.
  - **Terms page in force:** the Census Bureau Open Government page
    (`https://www.census.gov/about/policies/open-gov.html`) archived as
    `terms.html` in every snapshot; checked sentence "publishes its data
    as open data, meaning it is freely available for use and re-use by the
    public"; the TIGER/Line 2025 technical documentation section 1.2 (17
    U.S.C. § 105) cited in the license notes and DATA-LICENSES. Drift
    quarantines with the new reason kind `terms` (data dictionary updated).
  - **ACS variable list:** pinned to `B01003_001` and `B08201_002` with
    MOEs (methodology.md names no codes; these are the fixture's and the
    `demographics` stage's); anything more is a methods-version bump.
  - **Runner fixes kept in this packet:** bounded retry of the install
    rename on `PermissionError`, and the state-file scrub now covering the
    repr-escaped data-root form (an actual absolute-path leak, fixed and
    pinned by test).
  - Routine (agent's call, logged): per-source filter placement is
    **stored as delivered, filtered at first read** for all three (state /
    nationwide files are the provider's units; keeping them byte-for-byte
    makes snapshots verifiable against the provider; the county filter
    lives in each adapter's `read`); real / fixture coexistence = same
    stage names, zones, and paths, different pipeline name (`real`) and
    root, state file refuses the other pipeline; snapshot ID pinned as
    `pipeline.SNAPSHOT_ID` (DAG paths must be static) with `acquire`
    re-using a verified existing snapshot and refusing a tampered one,
    `download.new_snapshot_dir` deriving `-N` IDs for ad-hoc use;
    manifest records the URL that delivered (alternate swapped in if it
    did) and, for multi-file ACS, the provider's directory; TIGER read
    from the zip in place (nothing extracted; guards at acquisition and
    admission); ACS annotation values and blanks → null at read (ADR-0004);
    sample manifests carry `synthetic: false` (real data subsets) with the
    subset named in `license_note`; the suite disables sockets.
- **Unresolved risks / questions:** none blocking. Notes for EP-5b: TIGER
  and CenPop are read in NAD 83 (EPSG:4269) as delivered, so the analysis
  CRS ADR must reproject from that; `-555555555` (controlled estimate) is
  nulled like every other annotation value at read, none occurs at tract
  level in this snapshot; the archived terms page's digest changes per
  fetch (documented, not a defect).
- **No-go areas touched:** none (no PHI, no secret, nothing under a tracked
  `public/` zone, snapshots gitignored, CI offline; CI samples are
  US-public-domain subsets with their status documented).
- `roadmap/README.md` packet row updated to `[x] 39a6828`.
- **Exact next packet: EP-5b** (curated spine, invariants, ADR-0007 analysis
  CRS, data cards).
