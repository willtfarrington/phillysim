---
ep: 16d
title: Documentation sync of the READMEs, method cards, claims, roadmap documents, ADR-0008 and the changelog against the code
size: M
model: claude-opus-5-5
effort: max
status: planned
---

# EP-16d — Documentation sync of the READMEs, method cards, claims, roadmap documents, ADR-0008 and the changelog against the code

**Milestone:** — (checkpoint 3) · **Size:** M · **Depends on:** EP-16c · **Parallel with:** — · **Split from:** EP-16 (2026-11-26, at pickup; the fourth of six parts)

## Outcome & value
The rest of item 2 of [EP-16](EP-16-checkpoint-3.md): what the repository
says about the pipeline, the routing stage, the toolchain, the zone and the
page is what the code and tests do, now that a routing stage exists and the
lock has moved (EP-16a) and the baselines are fresh (EP-16b). Drift is
fixed here when it is a documentation error, and recorded as a finding for
the owning packet or gate when it is a code gap.

## Scope
- in: statements about the pipeline, the routing stage, the toolchain, the
  zone and the page, checked against the code and tests, in
  `phillysim/README.md`, the root `README.md`, `site/README.md`, the three
  method cards (the travel-times stub included), `docs/CLAIMS.md`,
  `roadmap/architecture.md` (the stage table, rows 1 to 11),
  `roadmap/quality.md` (the test matrix, the AM-2 band wording),
  `roadmap/methodology.md` ("Validation" as clarified at EP-15),
  `roadmap/adr/0008-routing-toolchain-pins.md` and `CHANGELOG.md` (test
  counts, stage lists, file lists); kept as a literal checklist in the
  payload (item, evidence, pass / fixed / finding).
- out (explicit non-scope): the documents EP-16c checked (the dictionary,
  the data cards, DATA-LICENSES, sources.md); any code change beyond a
  one-line documentation-driven correction; the estimate review and the
  milestones.md rows (EP-16e); anything a claims-matrix rule forbids.

## Prerequisites & locked decisions
- prerequisites: EP-16c.
- locked decisions honored: docs/CLAIMS.md's wording rules for any prose
  touched (descriptive access measurement only); ADR-0006 (the version
  axes); ADR-0008 (the pins and the band as measured); the walk gate's
  reading (EP-15, methodology.md "Validation"); the fixture-only screenshot
  policy.
- dependencies: the working clone, its tests (`uv run pytest --collect-only`
  for test counts) and the CLI's `--help` texts.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: documentation edits stay inside
the claims matrix; no machine identifier or absolute path in a tracked file
(the diff scanned); a document that contradicts the code in a way that
changes a claim is surfaced to the owner, not rewritten silently.

## Likely components & contracts (proposed)
The documents listed under Scope (corrections only); this brief;
`roadmap/README.md` (this row).

## Implementation notes
Work document by document, statement by statement, against the code
(module docstrings, the CLI's help, `pipeline.SNAPSHOT_IDS`, the stage
registry) and the suite (`--collect-only` counts by file). The EP-9 and
EP-10 payloads show the drift such a sync usually finds (stale counts, a
stage row, a labeling status). The CHANGELOG is checked, not rewritten:
counts and lists in its released and Unreleased entries that the code
contradicts are corrected with a note.

## Acceptance criteria & evidence
- [ ] Each listed document checked; each checked statement recorded as pass
      or fixed; code gaps recorded as findings with an owning packet or
      gate.
- Evidence: the payload's checklist.

## Tests / validation
`pre-commit run --all-files`; the diff scanned for paths and identifiers.

## Resource budget
Trivial.

## Risks, rollback, stop condition
A document that contradicts the code on a claim → surfaced to the owner. A
code gap → a finding, not a fix. More documents out of date than the
session holds → stop at a coherent state and split here, never run long.
Rollback: documentation only (revert the commit).

## Documentation / ADR updates
The documents listed under Scope where they had fallen behind; the README
row. ADR-0008 only by a dated note if a measured fact there is stale.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row's Done cell updated to `☑` and its
  backticked commit
- exact next packet
