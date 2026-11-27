---
ep: 16f
title: M4 refinement-gate pre-read, EP-17 authored, and the checkpoint's acceptance evidence
size: M
model: claude-opus-5-5
effort: max
status: planned
---

# EP-16f — M4 refinement-gate pre-read, EP-17 authored, and the checkpoint's acceptance evidence

**Milestone:** — (checkpoint 3) · **Size:** M · **Depends on:** EP-16e · **Parallel with:** — · **Split from:** EP-16 (2026-11-26, at pickup; the last of six parts, carrying the set's acceptance evidence)

## Outcome & value
Item 7 of [EP-16](EP-16-checkpoint-3.md), and the set's close. The M4
refinement gate's inputs are listed, the questions it must answer written
down and any gap in the planning documents recorded as a finding; the gate
is authored as `EP-17-m4-refinement-gate.md` from the template, so that a
fresh agent can author the M4 packets from it and the carry-ins without
re-reading the whole baseline; the README opens an "M4 — Full ingest"
heading with EP-17 as its first row (a gate belongs to the milestone it
refines, unlike a checkpoint). The parent's acceptance boxes are ticked
with a pointer to the part that met each, and the M5 carry-in's first item
is trimmed once EP-16b has confirmed the cross-clone repeat.

## Scope
- in:
  1. The parent's item 7 as written: read milestones.md's M4 row (all v1
     sources snapshotted, conflated, hours parsed with a QA report; adapter
     contract tests; hours-coverage % published; conflation QA reviewed),
     the carry-in "M4 — SNAP retailer follow-ups" (the OSM
     `shop=supermarket` cross-check, the two out-of-tract rows, the thirteen
     coincident pairs, the farmers'-market overlap), sources.md's remaining
     v1 sources and their terms, OQ-D (market hours parse coverage) and OQ-E
     (the collaborative's name), methodology.md "Destination layers" and the
     hours model, the download-guard conventions (EP-5a) and per-source
     `SNAPSHOT_ID`s (EP-12), and the sizing rule (D-2); record the inputs,
     the questions and the gaps.
  2. Author `EP-17-m4-refinement-gate.md` from `_TEMPLATE.md` (front
     matter, `status: planned`, S or M as the pre-read finds under D-2): a
     documentation-only packet whose outcome is the M4 packet files (EP-18
     onward, each S or M, the carry-ins applied first), its README row under
     the new "M4 — Full ingest" heading.
  3. The set's close: the parent's acceptance boxes ticked with pointers;
     the M5 carry-in's first item trimmed; EP-16's row in "Estimate
     accuracy" completed; the Checkpoints paragraph's pointer to the fourth
     checkpoint (as EP-16e set it).
- out (explicit non-scope): authoring the M4 packets themselves (EP-17's
  work); any ADR (the gate puts M4's hard-to-reverse values in one with the
  owner); any code.

## Prerequisites & locked decisions
- prerequisites: EP-16e (no re-plan trigger fired; if one did, this part
  waits on the owner).
- locked decisions honored: the refinement-gate procedure EP-11 set for M3
  (a documentation-only packet that applies the carry-ins first, reads its
  pre-read, puts every hard-to-reverse value in an ADR with the owner, and
  authors its packets from the template); D-2 and D-3 (sizes, front matter,
  completion note); the split convention (new packets take the next free
  integer, never a suffix).
- dependencies: the planning documents under `roadmap/`; the private
  planning directory only by path, if the gate's inputs point there.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: EP-17 states no value that
needs an ADR as settled; its questions for the owner stay questions;
documentation edits stay inside the claims matrix; no machine identifier or
absolute path in a tracked file (the diff scanned).

## Likely components & contracts (proposed)
New `roadmap/EP-17-m4-refinement-gate.md`; `roadmap/README.md` (the M4
heading with EP-17's row, the document index, this row, the Checkpoints
paragraph); `roadmap/milestones.md` (the M5 carry-in trimmed; EP-16's
estimate row completed); `roadmap/EP-16-checkpoint-3.md` (the acceptance
boxes); `CHANGELOG.md`; this brief.

## Implementation notes
EP-11 (the M3 gate) is the model for EP-17: its scope, its pre-read list,
its ADR with the owner, its packet decomposition. The gate's job is to turn
the M4 row into S or M packets: the remaining sources through the guarded
path with per-source snapshot IDs; conflation with its QA report; hours
parsing with its coverage number. The owner review at the end of this part
covers, at least, EP-17 as authored and the checkpoint's close.

## Acceptance criteria & evidence
- [ ] M4 gate pre-read recorded (inputs, questions, gaps);
      `EP-17-m4-refinement-gate.md` exists, follows the template, is S or M,
      and has its README row under the new M4 heading.
- [ ] The parent's acceptance boxes ticked with a pointer to the part that
      met each; the M5 carry-in's first item trimmed; EP-16's estimate row
      complete.
- Evidence: the payload; CI on the closing commit after the owner's push.

## Tests / validation
`pre-commit run --all-files`; `crw roadmap <absolute path>` (the M4 phase
read, EP-17 the next brief, no problems).

## Resource budget
Trivial.

## Risks, rollback, stop condition
A planning gap that blocks the gate (a source with no terms record, a
method choice nothing settles) → recorded as a finding and put to the owner;
EP-17 says so rather than guessing. Rollback: documentation only (revert the
commit).

## Documentation / ADR updates
As under Likely components. No ADR.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row's Done cell updated to `☑` and its
  backticked commit
- exact next packet
