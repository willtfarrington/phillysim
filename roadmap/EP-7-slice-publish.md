# EP-7 — Thin-slice metric + public zone + license bucketing

**Status:** [ ] planned · **Milestone:** M2 · **Effort:** M (1–2 sessions, medium confidence) · **Parallel with:** —

## Outcome & value
The deliberately trivial slice metric — straight-line QA distance from tract
centroid to nearest supermarket-format point, **labeled QA-only, never a
published access measure** — flowing curated → public zone with
license-bucket labeling (this table is Bucket A until OSM enters at M3+),
build-time bin computation, and the publish-gate check (license labels,
bounds, no raw-path leakage). Proves the public-boundary machinery
end-to-end.

## Scope
- in: slice metric, bucket labeling, publish gate, public GeoJSON/CSV.
- out (explicit non-scope): real travel times (M3); site UI beyond EP-8's
  minimal page.

## Prerequisites & locked decisions
- prerequisites: EP-6.
- locked decisions honored: AM-1 / ADR-0003 bucket rules; the analytic schema
  contract; build-time bins.
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the public zone contains only
tract-level aggregates + facility points already public upstream; the publish
gate must be green before anything leaves curated.

## Likely components & contracts (proposed)
`src/phillysim/metrics/slice.py`; `src/phillysim/publish/{bucket,gate}.py`;
`data/public/` outputs (gitignored; artifacts only).

## Implementation notes
The publish gate is the reusable artifact here; the metric exists to prove
the plumbing and will be retained only as a QA column.

## Acceptance criteria & evidence
- [ ] Publish gate blocks an intentionally mislabeled file (negative test).
- [ ] Public GeoJSON/CSV validate against schema + bucket rules.
- Evidence: golden metric test; gate negative test; fixture integration.

## Tests / validation
Golden metric test; gate negative test; integration on fixture.

## Resource budget
Trivial.

## Risks, rollback, stop condition
Temptation to publish the QA metric as an access measure — prohibited; stop
and re-read methodology.md if it comes up.

## Documentation / ADR updates
Data dictionary (public schema v1).

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- exact next packet: EP-8
