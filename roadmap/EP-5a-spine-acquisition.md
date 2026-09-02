# EP-5a — Spine source adapters: acquisition path + TIGER/CenPop/ACS snapshots

**Status:** [ ] planned · **Milestone:** M2 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-5 (2026-09-02, EP-9 pre-read; EP-5b is the other half)

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
- [ ] From a fresh clone, a manual `phillysim run --stage validate`
      acquires the three snapshots, admits them, and `phillysim verify`
      passes on the real data root (counts, sizes, and timings recorded).
- [ ] Every manifest carries `terms_archive`, `license_bucket = "A"`, and a
      `license_note`; the archived terms page is present and checksummed.
- [ ] Contract tests for the three sources green in CI on the committed
      samples; `uv run pytest` green; no test reaches the network.
- [ ] Guard `Limits` confirmed per source and recorded in the handoff.
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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results (real-run counts, sizes,
  timings; CI run ID)
- resource observations
- decisions/ADRs made (per-source filter placement; real/fixture pipeline
  coexistence; confirmed limits); unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated to `[x] <commit>`
- exact next packet: EP-5b
