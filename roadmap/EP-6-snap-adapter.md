# EP-6 — SNAP retailer adapter + supermarket-format classification

**Status:** [ ] planned · **Milestone:** M2 · **Effort:** M (1–2 sessions, medium confidence) · **Parallel with:** —

## Outcome & value
SNAP retailer acquisition (manifest-recorded), Philadelphia filter, a
store-type → format-class mapping table (published in the method card;
**format-based names only**), a point GeoParquet layer keyed by stable site
ID, and the all-SNAP-retailer variant retained for M5's SRAM validation. The
OSM supermarket cross-check is deferred to M4 conflation (noted, not
implemented).

## Scope
- in: adapter, filter, classification mapping + method-card stub, point
  layer, sanity counts.
- out (explicit non-scope): conflation/dedup across sources (M4); hours (the
  SNAP file has none).

## Prerequisites & locked decisions
- prerequisites: EP-5.
- locked decisions honored: AM-4 (SNAP-derived supermarket-format points);
  the claims-vocabulary ban (no nutrition-quality adjectives on
  project-derived categories — including in code identifiers).
- dependencies: USDA SNAP retailer file (dual-URL manifest field — FNS→FNA
  domain migration in progress).

## Safety preconditions
Standing policy (see EP-1). Packet-specific: classification wording reviewed
against docs/CLAIMS.md before merge.

## Likely components & contracts (proposed)
`src/phillysim/adapters/snap.py`;
`src/phillysim/classify/store_format.py` + mapping table in config;
`tests/contracts/test_snap.py`.

## Implementation notes
Store-type mapping is a published, versioned artifact (methods axis): keep it
in config, render it into the method-card stub.

## Acceptance criteria & evidence
- [ ] Classified point layer reproducible from fresh clone.
- [ ] Mapping table renders into the method-card stub.
- [ ] Philadelphia counts sanity-checked against the source's own totals
  (recorded in handoff).
- Evidence: contract tests + golden mapping test green.

## Tests / validation
Contract tests on fixture; golden mapping test.

## Resource budget
Trivial.

## Risks, rollback, stop condition
Store-type field semantics differ from documentation → stop, record evidence,
adjust the mapping with a methods-version note.

## Documentation / ADR updates
Method-card stub (destination layers); data card (SNAP).

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- exact next packet: EP-7
