---
ep: N
title: <title>
size: S
model: <the model's id>
effort: <the effort level>
status: planned
---

# EP-N — <title>

**Milestone:** M_ · **Size:** S · **Depends on:** EP-k · **Parallel with:** —

> Sizing rule (README "Packet sizing and splitting", D-2): a packet is S
> (about 30 minutes of active work) or M (about 45), never L. If the
> outcome needs more, author two packets with consecutive integers. A
> packet that proves larger at pickup is split there, never run long: it
> keeps its number, uses `EP-Na-<slug>.md` / `EP-Nb-<slug>.md` file names,
> and appends `· **Split from:** EP-N` to the header line. The front
> matter (D-3) is kept true to the session: `status` is `planned` when a
> gate authors the packet, `in progress` while its session works and
> `done` at its close; `model` and `effort` are the session's. Add the
> packet's row to the milestone table in README.md when the file is
> created. Delete this note.

## Outcome & value
<one paragraph: what exists after this packet and why it matters to the user or the science>

## Scope
- in:
- out (explicit non-scope):

## Prerequisites & locked decisions
- prerequisites: <packets/milestones>
- locked decisions honored: <ADR/baseline references>
- dependencies: <sources, tools>

## Safety preconditions
<the data/license/privacy/security/accessibility/claims checks this packet must respect — "none beyond standing policy" is a valid entry only if true>

## Likely components & contracts (proposed)
<files/modules expected to be touched; input/output contracts; all labeled proposed until implemented>

## Implementation notes
<enough to orient a fresh agent without dictating code>

## Acceptance criteria & evidence
- [ ] <observable criterion>
- Evidence: <tests passing, artifact produced, review recorded>

## Tests / validation
<commands or manual steps>

## Resource budget
<CPU/RAM/disk/network/runtime if relevant; "trivial" acceptable>

## Risks, rollback, stop condition
<risk → rollback; the condition that means stop and escalate to owner>

## Documentation / ADR updates
<what must be updated before the packet closes>

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row's Done cell updated to `☑` and its
  backticked commit (and the milestone heading, if this was its last
  packet and the go/no-go holds)
- exact next packet

> **Completion note (YYYY-MM-DD; model/effort; duration).** What was built;
> each owner decision and its outcome; the routine choices; notes for later
> sessions. The handoff payload above is the detailed record.
