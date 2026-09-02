# EP-5 — Geography spine adapters: TIGER + CenPop + ACS

**Status:** split 2026-09-02 into [EP-5a](EP-5a-spine-acquisition.md) and [EP-5b](EP-5b-spine-curated.md) · **Milestone:** M2 · **Effort:** M (1–2 sessions, high confidence), as authored · **Parallel with:** —

> **This file names the set, not a packet.** The EP-9 checkpoint's pickup
> pre-read (README "Packet sizing and splitting") found that this brief
> holds two first-time subsystems, the outbound acquisition path with three
> adapters and the real-data spine with its invariants and CRS decision,
> each comparable to one of the EP-4 halves that filled a session. It was
> split at the boundary the implementation notes allow: **EP-5a** acquires
> (download path, TIGER / CenPop / ACS adapters, contracts, samples, real
> pipeline registration) and **EP-5b** curates (spine, invariant tests,
> ADR-0007 analysis CRS, data cards) and carries this set's milestone-level
> evidence below. References to "EP-5" elsewhere mean both parts; the text
> below is the brief as authored on 2026-08-23.

## Outcome & value
Real acquisition scripts (manifest-recorded, checksummed, bbox-filtered at
ingest) for TIGER/Line 2025 Philadelphia tracts, CenPop2020 population-
weighted centroids, and ACS 5-yr 2020–2024 selected tables with MOE; a
curated GeoParquet spine keyed by GEOID; geospatial invariant tests (CRS,
geometry validity, county bounds, 2020-vintage GEOID integrity, join
cardinality).

## Scope
- in: three adapters, curated spine, invariant tests, analysis-CRS decision.
- out (explicit non-scope): destination sources (EP-6); metrics (EP-7).

## Prerequisites & locked decisions
- prerequisites: EP-4b (and therefore EP-4a).
- locked decisions honored: 2020 tracts; pinned vintages (sources.md); the
  analysis CRS is chosen and ADR'd **in this packet**.
- dependencies: Census/TIGER endpoints (documented in outbound allowlist).

## Safety preconditions
Standing policy (see EP-1). Packet-specific: Census terms honored; snapshots
stay in the gitignored raw zone; only fixture-scale samples become CI
fixtures, and only with their permissive redistribution documented (US public
domain — document it).

## Likely components & contracts (proposed)
`src/phillysim/adapters/{tiger,cenpop,acs}.py`;
`tests/contracts/test_spine.py`; ADR for the analysis CRS.

## Implementation notes
Bbox/county filter at ingest (early-filtering rule). ACS variables limited to
those methodology.md names; anything more requires a methods-version bump.

## Acceptance criteria & evidence
- [ ] `phillysim run --stage spine` from a fresh clone reproduces the
  checksummed curated spine.
- [ ] Invariant tests green; MOE columns present.
- Evidence: contract + invariant suites in CI (fixtures); a real run
  documented in the handoff.

## Tests / validation
Contract + invariant suites (CI on fixtures; real run manual, recorded).

## Resource budget
Network: a few hundred MB. Disk: <2 GB. Runtime: minutes.

## Risks, rollback, stop condition
ACS table-selection creep → stop at methodology.md's variable list.
Endpoint URL drift → dual-URL manifest field; record and continue.

## Documentation / ADR updates
Data cards (spine sources); CRS ADR.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- exact next packet: EP-6
