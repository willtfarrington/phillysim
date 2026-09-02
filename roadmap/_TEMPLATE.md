# EP-N — <title>

**Status:** [ ] planned · **Milestone:** M_ · **Effort:** S (1 session, confidence) · **Parallel with:** —

> Sizing rule (README "Packet sizing and splitting"): one packet is one
> session. If the outcome needs more, author two packets with consecutive
> integers. A packet split at pickup keeps its number, uses
> `EP-Na-<slug>.md` / `EP-Nb-<slug>.md` file names, and appends
> `· **Split from:** EP-N` to the header line. Add the packet's row to the
> milestone table in README.md when the file is created. Delete this note.

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
- `roadmap/README.md` packet row updated to `[x] <commit>` (and the
  milestone heading, if this was its last packet and the go/no-go holds)
- exact next packet
