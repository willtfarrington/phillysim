# EP-4a — Manifest/snapshot engine + zones + download guards

**Status:** [ ] planned · **Milestone:** M1 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-4 (2026-09-02; EP-4b is the other half)

## Outcome & value
The data half of the pipeline backbone: snapshot IDs and the immutable
raw→intermediate→curated→public zone layout under `data/` (plus quarantine
and cache), checksummed manifests carrying the ADR-0006 version-axis fields
(acquisition URL + dual-URL field, terms-archive pointer, schema version,
license bucket, per-file SHA-256), a quarantine path for validation
failures, and download guards (size caps, zip-slip, decompression-bomb,
domain allowlist) — proven against the tinycity raw snapshots. EP-4b builds
the stage runner on top of this.

## Scope
- in: zone layout + snapshot IDs; manifest model, writer, reader, and
  checksum verification; quarantine-on-failure; download/extraction guards
  with negative tests; `phillysim verify --fixture` at the snapshot level
  (every raw snapshot matches its manifest); promotion of the tinycity
  manifest shape from "proposed" to owned (regenerate the fixture if the
  shape changes).
- out (explicit non-scope): stages, fingerprints, resume/cancel, preflight,
  `phillysim run/status` (EP-4b); real adapters (EP-5/6); drift detection
  beyond schema-hash comparison.

## Prerequisites & locked decisions
- prerequisites: EP-3.
- locked decisions honored: architecture.md zones & identifiers; ADR-0006
  version-axis fields in manifests; ADR-0002 storage; ADR-0003 license
  bucket recorded per snapshot; EP-2's data-root resolution (resolution
  never creates directories).
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: quarantine-on-failure is
default-deny; `data/` gitignored; manifests contain no machine identifiers
or absolute paths; guards are tested against crafted malicious inputs, never
against real downloads (no network in this packet).

## Likely components & contracts (proposed)
`src/phillysim/{zones,manifest,guards}.py`; `phillysim verify --fixture`
(snapshot-level; EP-4b extends it with stage state); tests
`tests/test_zones.py`, `tests/test_manifest.py`, `tests/test_guards.py`.
Input contract: the tinycity `raw/<source>/<snapshot-id>/manifest.json`
shape in `docs/data-dictionary.md` (schema version 1). Output contract: a
manifest the reader round-trips byte-for-byte and `verify` accepts.

## Implementation notes
Snapshot ID = date-stamped per-source identifier (architecture.md); the
manifest is the only place version-axis fields are recorded. Quarantine
moves the offending snapshot directory whole and writes a reason file next
to it; nothing in quarantine is ever read by a later stage. Guards operate
on local file objects so they are testable offline: size cap before and
during extraction, path normalization against the target root (zip-slip),
compression-ratio ceiling (bomb), and an allowlist check on the acquisition
URL host. Keep the module free of adapter knowledge.

## Acceptance criteria & evidence
- [ ] All eight tinycity raw snapshots verify against their manifests; a
      tampered byte in one data file makes `verify` fail naming the file.
- [ ] Injected oversized, zip-slip, decompression-bomb, and off-allowlist
      inputs are each refused and quarantined (negative tests, one per
      guard).
- [ ] Manifest round-trip is byte-identical; missing or malformed
      version-axis fields are rejected.
- Evidence: pytest suite green locally and in CI (Windows + Linux); data
  dictionary manifest section no longer labeled "proposed".

## Tests / validation
`uv run pytest`; guard negative tests; fixture regeneration if the manifest
shape changed (`phillysim gen-tinycity --out …` for both variants, then
`test_committed_fixture_matches_regeneration`).

## Resource budget
Trivial at fixture scale.

## Risks, rollback, stop condition
Manifest-shape churn → hold to the data-dictionary shape plus ADR-0006
fields; anything else belongs to EP-4b or later. Stop if the guards need
network access to test — they must not.

## Documentation / ADR updates
`docs/data-dictionary.md` manifest section (proposed → owned; schema
version unchanged unless a field is added, then bump with a migration note);
package README layout list; packet row in `roadmap/README.md`.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated
- exact next packet: EP-4b
