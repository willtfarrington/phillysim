---
ep: 16e
title: Estimate-accuracy review with the M3 actual, the re-plan triggers, and v1 counted in briefs under D-2
size: M
model: claude-opus-5-5
effort: max
status: planned
---

# EP-16e — Estimate-accuracy review with the M3 actual, the re-plan triggers, and v1 counted in briefs under D-2

**Milestone:** — (checkpoint 3) · **Size:** M · **Depends on:** EP-16d · **Parallel with:** — · **Split from:** EP-16 (2026-11-26, at pickup; the fifth of six parts)

## Outcome & value
Item 6 of [EP-16](EP-16-checkpoint-3.md), with the count inbox IN-2 and
IN-3 ask for. The "Estimate accuracy" table in `roadmap/milestones.md` has
its EP-15 and M3 rows confirmed and an EP-16 row (the set: one session as
authored, six M parts under D-2); the implication note says what the M3
actual means against EP-10's rule (the gate's packet count replaces the
range; the high bound is the planning number); the three re-plan triggers
are evaluated with EP-16b to EP-16d's results; the checkpoint cadence
("every ~5 packets", set under the old sizes) is re-read under D-2; any
re-sizing of M4 to M8 is proposed to the owner, not applied. And the
remaining v1 work (M4 to M7 with their gates and checkpoints) is restated as
a count of briefs under D-2, from milestones.md's high bounds and the M3
actual, with the owner settling which rows carry it (gate rows, provisional
rows or none), so that the count Roadmap Wrangler's site export reads says
how far v1 runs.

## Scope
- in:
  1. The parent's item 6 as written: confirm the EP-15 and M3 rows (written
     by EP-15's closing session); append EP-16 (parts a to e actual, f
     planned, the row completed by EP-16f); rewrite the implication note
     with the M3 actual (EP-11 authored four S packets and the box, EP-13 to
     EP-15, took four attended sessions: record what the count predicted and
     what it missed, the closing session the hand check's tally forced);
     evaluate the three re-plan triggers and record the result; propose, not
     apply, any re-sizing of the M4 to M8 ranges for the owner's decision.
  2. The checkpoint cadence re-read under D-2 (sessions of about 30 or 45
     minutes, not the older sittings), the fourth checkpoint's due point
     stated, and milestones.md "Spikes & gates" pointed at it.
  3. From IN-2: v1's remaining work counted in briefs under D-2 (M4 7, M5 7,
     M6 10 and M7 4 sessions at the high bounds, sized before D-2; 4
     refinement gates; about 6 checkpoints), the rows that carry it settled
     with the owner and written into the tables if the owner so decides; the
     README's "How far v1 runs" paragraph updated.
  4. From IN-3: when the rows cover v1, a `> **Handed on (to prime).**`
     block, so that prime's IN-5 drops the portfolio card's floor of 57.
- out (explicit non-scope): applying a re-sizing the owner has not
  approved; authoring M4 packets (EP-17's work); the M4 pre-read itself
  (EP-16f).

## Prerequisites & locked decisions
- prerequisites: EP-16d (the re-run and both sweeps done, so the drift
  trigger can be read).
- locked decisions honored: milestones.md's checkpoint definition and
  re-plan triggers; the owner's decision of 2026-09-03 (plan against the high
  bounds; each gate's packet count replaces its milestone's range at the
  checkpoint that follows it); D-2 (S about 30 minutes, M about 45, no L).
- dependencies: the packet handoffs for actuals; the session transcripts
  for timings where a handoff is silent (devenv memory "Re-plan timing").

## Safety preconditions
Standing policy (see EP-1). Packet-specific: no re-sizing applied without
the owner's word; provisional rows, if the owner chooses them, are marked so
that no session takes one for an authored brief; nothing outward-facing
beyond the hand-on to prime, which crw delivers.

## Likely components & contracts (proposed)
`roadmap/milestones.md` ("Estimate accuracy", the implication note, the
trigger evaluation, "Spikes & gates"); `roadmap/README.md` ("How far v1
runs", the Checkpoints paragraph, rows if the owner so decides); this brief.

## Implementation notes
At IN-3's own reckoning (2026-11-26), the card's floor of 57 is the 19 rows
then in the tables plus 28 milestone sessions, 4 gates and about 6
checkpoints. The split of EP-16 took the tables to 24 rows, which is 62 by
the same sum before any D-2 restatement. Restating sessions of the older
size as S or M briefs can only raise the count. So the count is not expected
to come in under 57, and nothing was said to prime at once. The count still
needs this packet's evidence: the M3 actual in sessions and in active time,
EP-16's six parts, and how the older sittings map to D-2 briefs. Check
Roadmap Wrangler's reading after any row change (`crw roadmap` with the
project's absolute path: the bare name resolves to the package folder).

## Acceptance criteria & evidence
- [ ] "Estimate accuracy" confirmed for EP-15 and M3 and extended with
      EP-16; the implication note rewritten with the M3 actual; the three
      re-plan triggers evaluated and recorded; any re-sizing proposed to the
      owner and the answer recorded.
- [ ] The cadence re-read and the fourth checkpoint's due point stated.
- [ ] v1 counted in briefs under D-2; the owner's choice of rows recorded
      and applied; "How far v1 runs" updated; the hand-on to prime written
      when the rows cover v1.
- Evidence: the payload; `crw roadmap` read after the change.

## Tests / validation
`pre-commit run --all-files`; `crw roadmap <absolute path>` (no problems,
the counts expected).

## Resource budget
Trivial.

## Risks, rollback, stop condition
A re-plan trigger fires → **stop** and surface it to the owner instead of
proceeding to EP-16f. Rollback: documentation only (revert the commit).

## Documentation / ADR updates
milestones.md and README as above. No ADR.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row's Done cell updated to `☑` and its
  backticked commit
- exact next packet
