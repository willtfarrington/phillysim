# EP-3 — tinycity synthetic fixture

**Status:** [ ] planned · **Milestone:** M1 · **Effort:** M (1–2 sessions, high confidence) · **Parallel with:** —

## Outcome & value
A deterministic synthetic mini-geography ("tinycity": ~6 fake tracts, fake
POIs of all three destination categories with hours edge cases, tiny fake
network/GTFS stubs where cheap) with generator script and golden files,
sufficient to exercise every pipeline stage offline — plus the
source-contract test harness pattern (schema/license/geometry expectations)
proven against one fake source.

## Scope
- in: fixture generator, golden files, contract-harness pattern + one fake
  source contract, hours edge cases.
- out (explicit non-scope): real source adapters; routing (fixture provides
  precomputed fake travel times for downstream stages until M3).

## Prerequisites & locked decisions
- prerequisites: EP-2.
- locked decisions honored: the analytic schema contract {estimate, MOE, CV
  tier, reliability_action}; hours edge cases informed by methodology.md
  Tier 2 (weekend-only market, seasonal market, missing hours, malformed
  hours string).
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: fixture is wholly synthetic — no
derived real data; permissively licensed by construction (document that in
the fixture README).

## Likely components & contracts (proposed)
`tests/fixtures/tinycity/` + `tools/gen_tinycity.py`; `tests/contracts/`
harness; golden Parquet/GeoJSON files.

## Implementation notes
Determinism is the point: fixed seeds, stable ordering, identical checksums
on regeneration. Include at least one deliberately invalid variant for
negative testing.

## Acceptance criteria & evidence
- [ ] Fixture generation deterministic (same checksums on two runs).
- [ ] Contract harness catches an injected schema violation (negative test).
- Evidence: pytest contract suite green in CI; fixture README.

## Tests / validation
pytest contract suite in CI.

## Resource budget
Trivial.

## Risks, rollback, stop condition
Fixture over-engineering — stop at "exercises every stage," not realism.

## Documentation / ADR updates
Fixture README; data dictionary seeded.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- exact next packet: EP-4
