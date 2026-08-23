# EP-4 — Manifest/snapshot engine + zones + stage runner

**Status:** [ ] planned · **Milestone:** M1 · **Effort:** L (2 sessions, medium confidence; split allowed at engine/runner boundary) · **Parallel with:** —

## Outcome & value
The pipeline backbone: snapshot IDs, checksummed manifests (acquisition URL +
dual-URL field, terms-archive pointer, schema version, license bucket),
raw→intermediate→curated→public zone layout under `data/`, an idempotent
stage runner with input fingerprints (unchanged inputs → skip stage),
resume/cancel semantics, preflight checks (disk/RAM/deps), a quarantine path
for validation failures, and download guards (size caps, zip-slip,
decompression-bomb, domain allowlist) — all proven on tinycity.

## Scope
- in: everything above, fixture-proven.
- out (explicit non-scope): real adapters (EP-5/6); drift detection beyond
  schema-hash comparison.

## Prerequisites & locked decisions
- prerequisites: EP-3.
- locked decisions honored: architecture.md zones/stages; ADR-0006 version-
  axis fields in manifests; ADR-0002 storage.
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: quarantine-on-failure is
default-deny; `data/` gitignored; manifests contain no machine identifiers.

## Likely components & contracts (proposed)
`src/phillysim/{manifest,zones,stages,preflight,guards}.py`; CLI verbs
`phillysim run/status/verify --fixture`.

## Implementation notes
Fingerprint = content hash of inputs + parameters; anything fancier is out of
scope. Cancellation must leave a state `verify` can report as coherent.

## Acceptance criteria & evidence
- [ ] Full fixture pipeline runs end-to-end; re-run skips unchanged stages.
- [ ] Kill mid-stage → `phillysim verify` reports coherent state.
- [ ] Injected oversized / zip-slip fixture is quarantined (negative tests).
- Evidence: integration suite green on tinycity in CI.

## Tests / validation
Integration suite on tinycity; guard negative tests.

## Resource budget
Trivial at fixture scale.

## Risks, rollback, stop condition
Fingerprint design churn → hold to content-hash + params. Stop if the
engine/runner split is needed (allowed) — end session at the engine boundary
tested.

## Documentation / ADR updates
Pipeline README section; data dictionary update.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- exact next packet: EP-5
