---
ep: 16c
title: License-label sweep on the real published output and the Bucket B zone; the dictionary, data cards and license records checked
size: M
model: claude-opus-5-5
effort: max
status: planned
---

# EP-16c — License-label sweep on the real published output and the Bucket B zone; the dictionary, data cards and license records checked

**Milestone:** — (checkpoint 3) · **Size:** M · **Depends on:** EP-16b · **Parallel with:** — · **Split from:** EP-16 (2026-11-26, at pickup; the third of six parts)

## Outcome & value
Item 3 of [EP-16](EP-16-checkpoint-3.md) and the data half of its item 2.
Every license label on the real published output is traceable to a source
record; the public zone is still Bucket A only (nothing derived from the
OSM network is published before M5); the curated matrix and the night
records are Bucket B by derivation and say so where the dictionary says
they do; nothing is tracked under a public zone, `site/dist/`, `data/` or
the toolchain directories. And the data-facing documents match the code:
the data dictionary covers every file the real pipeline writes (or lists it
as intermediate by policy), and the seven data cards with their index,
`docs/DATA-LICENSES.md` and `roadmap/sources.md` say what the adapters do. A
license contradiction is a stop.

## Scope
- in:
  1. The parent's item 3 as written, on the working clone's installed real
     public zone (byte-equal to the fresh clone's by EP-16b's comparison):
     each file's bucket equals the bucket derived from its listed sources'
     raw manifests; its attribution lines equal the adapters' citations and
     the DATA-LICENSES records; the sources' `license_note` texts agree with
     those records; `publish` does not read the matrix; `git ls-files` shows
     nothing under any `public/` zone, `site/dist/`, `data/`,
     `phillysim/.jdk/` or `phillysim/.r5/`; the SEPTA feed's terms as
     recorded still hold; the ODbL notice sentence stays flagged for legal
     review at M6.
  2. Item 2 for four documents: `docs/data-dictionary.md` against every
     file the real pipeline writes (the seven raw snapshots with manifests
     and archived pages; the intermediate files, `intermediate/network/` and
     `intermediate/travel_times.json` included; the curated tables,
     `travel_times.parquet` included; the public files; the state file; the
     night directories under `runs/routing/` with their run records,
     `verdict.json`, `handcheck/` and `concordance/`); the seven data cards
     and their index; `docs/DATA-LICENSES.md`; `roadmap/sources.md`.
  3. Findings kept as literal checklists in the payload (item, evidence,
     pass / fixed / finding).
- out (explicit non-scope): the other documents of item 2 (EP-16d); any
  code change beyond a one-line documentation-driven correction (a code gap
  becomes a finding for its owning packet or gate); the ODbL notice's legal
  review (M6); any write under a data zone.

## Prerequisites & locked decisions
- prerequisites: EP-16b green (the references confirmed from a fresh
  clone).
- locked decisions honored: ADR-0003 (the license buckets; the matrix is
  Bucket B), ADR-0005 (the basemap), docs/CLAIMS.md's wording rules for any
  prose touched, the SEPTA terms and the facts-not-contents position as
  recorded in DATA-LICENSES.
- dependencies: the working clone's real data root, read only.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the real data root is read,
never written; nothing under a public zone or `site/dist/`; documentation
edits stay inside the claims matrix; no machine identifier or absolute path
in a tracked file (the diff scanned); a license contradiction or a tracked
file under a public zone is a stop condition.

## Likely components & contracts (proposed)
`docs/data-dictionary.md`, `docs/data-cards/*.md`, `docs/DATA-LICENSES.md`,
`roadmap/sources.md` (corrections only); `CHANGELOG.md`; this brief;
`roadmap/README.md` (this row).

## Implementation notes
Read `public/manifest.json` and the raw manifests with a small
standard-library script in the session's scratchpad that derives each
file's bucket and lists its attribution lines beside the adapters'
citations, so the checklist is generated, not typed. List what the real data
root holds by path with a script, never by hand, and set it against the
dictionary's entries. The EP-10 sweep's checklist (its payload) is the model
for this one.

## Acceptance criteria & evidence
- [ ] License-label sweep checklist complete with no open contradiction;
      the public zone Bucket A only; `git ls-files` shows no file under any
      `public/` zone, `site/dist/`, `data/` or the toolchain directories.
- [ ] Every real-pipeline-written file documented in the dictionary or
      listed as intermediate by policy.
- [ ] The data cards, their index, DATA-LICENSES and sources.md checked,
      each statement recorded as pass or fixed; code gaps recorded as
      findings with an owning packet or gate.
- Evidence: the payload's checklists.

## Tests / validation
`pre-commit run --all-files`; the diff scanned for paths and identifiers.

## Resource budget
Trivial: reads of the data root and the documents.

## Risks, rollback, stop condition
A license contradiction → **stop** and surface it to the owner. A code gap →
a finding for its owning packet or gate, not a fix here. Rollback:
documentation only (revert the commit).

## Documentation / ADR updates
The four documents above where they had fallen behind; `CHANGELOG.md`; the
README row. No ADR.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row's Done cell updated to `☑` and its
  backticked commit
- exact next packet
