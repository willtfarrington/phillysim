---
ep: 16b
title: Fresh-clone re-run, fixture and real, with the routing night; resource use against the budgets, peak RSS included
size: M
model: claude-opus-5-5
effort: max
status: planned
---

# EP-16b — Fresh-clone re-run, fixture and real, with the routing night; resource use against the budgets, peak RSS included

**Milestone:** — (checkpoint 3) · **Size:** M · **Depends on:** EP-16a, and its push (OT-1) · **Parallel with:** — · **Split from:** EP-16 (2026-11-26, at pickup; the second of six parts)

## Outcome & value
Items 1 and 4 of [EP-16](EP-16-checkpoint-3.md). A fresh clone of the
pushed `main`, carrying the lock [EP-16a](EP-16a-dependency-triage.md) left,
re-run green, fixture and real: its ten real stages from an empty data root
reproduce every raw, curated and public digest byte for byte, and the
`travel_times` stage routes a night of its own whose matrix digests equal the
spike's night and the second night (the cross-clone determinism repeat the
M5 carry-in asks for). The run's resource use, peak process-tree RSS
included for the first time at a checkpoint, is recorded against the budgets
and appended to "Resource baselines". This part's result decides whether
the rest of the checkpoint is a checkpoint or a stop (the trigger
"checkpoint finds drift").

## Scope
- in:
  1. The parent's item 1 as written: the clone (`git clone -c
     core.longpaths=true`, into a scratch directory outside the working
     clone); `uv sync --locked --group routing`; `phillysim toolchain
     install` and `toolchain check`; `uv run pytest`; the fixture verbs (`run
     --fixture` twice, `status`, `verify`, `gate`, `site build`, all
     `--fixture`); the real pipeline from an empty data root (`run`, the
     night attended this once and the machine kept awake; `run` again;
     `status`; `verify`; `gate`; `site build`; `route status`; `route
     verdict --night <the new night>`, mechanical criteria only); every raw
     data-file digest in the seven snapshot manifests and every curated and
     public digest compared with the EP-8b, EP-12 and EP-15 handoffs'
     references, the matrix's canonicalized-value and byte digests
     included. The archived terms pages (not byte-stable since EP-5a) and
     r5py's rebuilt network cache are not compared.
  2. The parent's item 4 as written: per-stage wall time; acquisition bytes
     and seconds per source; the night's walls and peak process-tree RSS per
     run against the 20 GB budget and the 22 GB kill; the toolchain install;
     the second run and the `status`, `verify`, `gate` and `site build`
     times; the suite's time with the routing group; CI duration per
     platform on EP-16a's pushed commit; the data root's size by zone (the
     cache, r5py's network cache) against the 50 GB workspace budget; the
     public zone raw and gzipped; the built site; the preflight report.
     Appended to "Resource baselines" in `phillysim/README.md`.
  3. CI on EP-16a's pushed commit read and recorded (green on both
     platforms, or the failure surfaced).
- out (explicit non-scope): any fix beyond a one-line documentation-driven
  correction (larger defects become findings for the owning packet); a
  controlled refresh of a snapshot (a provider-bytes mismatch is a finding
  and a stop, not a refresh); the hand check and the concordance (done once
  on the spike's night); the license sweep and the documentation sync
  (EP-16c, EP-16d); any dependency change.

## Prerequisites & locked decisions
- prerequisites: EP-16a done and its commits pushed by the owner (OT-1):
  the clone reads the pushed `main`.
- locked decisions honored: the parent's list: ADR-0003 (the matrix is
  Bucket B), ADR-0006, ADR-0007, ADR-0008 (the pins, the band, the routing
  group's layout), the download-path order and the terms-archive stop
  condition (EP-5a), quality.md's determinism criterion (the
  canonicalized-value digests), the fixture-only screenshot policy.
- dependencies: the seven providers at their pinned URLs (unchecked since
  the last fresh acquisitions, EP-10 and EP-12, 2026-09-03); GitHub and PyPI;
  the JDK and jar hosts through `toolchain install`; the machine awake for
  the night (about a quarter of an hour).

## Safety preconditions
The parent's: the scratch clone is deleted at the end, its data root,
toolchain and caches with it; acquisition goes only through the guarded path
(allowlists, caps, terms check, quarantine); nothing is written under a
tracked `public/` zone or `site/dist/`; no machine identifier or absolute
path enters a tracked file (the diff scanned); a provider-bytes mismatch, a
matrix digest that differs from the recorded nights, or a tracked file
under a public zone is a stop condition, not something to paper over in
prose.

## Likely components & contracts (proposed)
`phillysim/README.md` ("Resource baselines" appended); this brief;
`roadmap/README.md` (this row); `CHANGELOG.md` (one line). No code; a
one-line correction only if the re-run demands it, recorded in the payload.

## Implementation notes
The references: the EP-8b handoff (public and curated digests), the EP-12
handoff (the two routing snapshots and the clip), the EP-15 handoff (both
nights' core-run matrix digests, walk `100625cd…` and transit `e35b466d…`;
the curated matrix, value digest `fc50873d…`, byte digest `f2ed818a…`).
Generate the comparison table with a small standard-library script kept in
the session's scratchpad and run through `uv run --project`, rather than
typing digests. `phillysim run` has no `--keep-awake` (`route matrix` has):
keep the machine awake by hand, or launch the stage the detached way the
phillysim README records. Whether the seven providers still serve the
pinned files is the first thing the run learns: a failed or changed fetch is
this packet's stop and an owner decision on a controlled refresh, never a
re-pin here. If the run will not fit the session, stop at a coherent state
and split here (the re-run, then the baselines), never run long.

## Acceptance criteria & evidence
- [ ] Fresh-clone re-run green, fixture and real: `uv sync --locked --group
      routing`, the toolchain installed and checked, `uv run pytest`, the
      fixture verbs (11 ran, then 0 ran / 11 skipped; 11 fresh; 8 of 8
      snapshots, 11 of 11 stages; gate green; site built), the real pipeline
      from empty (10 ran including a routing night, then 0 ran / 10 skipped;
      10 fresh; 7 of 7 snapshots, 10 of 10 stages; gate green; site built),
      with counts and timings in the payload; every provider data-file
      digest and every curated and public digest equal to the references,
      the matrix's included.
- [ ] Baselines recorded in the payload and appended to "Resource
      baselines", compared with the budgets, peak RSS included.
- [ ] CI on EP-16a's commit recorded, green on Windows and Linux or its
      failure surfaced.
- Evidence: the payload's tables; the scratch clone deleted.

## Tests / validation
The commands of item 1 in the clone; `pre-commit run --all-files` in the
working clone; the diff scanned for paths and identifiers.

## Resource budget
Attended: one M session, about a quarter of an hour of it the routing
night, plus the seven acquisitions (the Geofabrik extract the largest).
Disk: the scratch clone's data root, the JDK, r5py's cache, deleted at the
end. Network: the seven providers once, PyPI and the toolchain hosts once.

## Risks, rollback, stop condition
The re-run fails → **stop**; that is the trigger "checkpoint finds drift",
surfaced to the owner. A provider file's bytes differ → a finding and an
owner decision on a controlled refresh, a stop. A matrix digest differs
from the recorded nights → a determinism finding for the owner (OQ-C's
procedure, ADR-0008), a stop. Rollback: documentation only; the scratch
clone is deleted whatever the outcome.

## Documentation / ADR updates
`phillysim/README.md` "Resource baselines"; `CHANGELOG.md`; the README row.
No ADR.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row's Done cell updated to `☑` and its
  backticked commit
- exact next packet
