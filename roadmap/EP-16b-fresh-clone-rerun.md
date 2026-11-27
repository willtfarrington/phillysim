---
ep: 16b
title: Fresh-clone re-run, fixture and real, with the routing night; resource use against the budgets, peak RSS included
size: M
model: claude-opus-5-5
effort: max
status: done
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
- [x] Fresh-clone re-run green, fixture and real: `uv sync --locked --group
      routing`, the toolchain installed and checked, `uv run pytest`, the
      fixture verbs (11 ran, then 0 ran / 11 skipped; 11 fresh; 8 of 8
      snapshots, 11 of 11 stages; gate green; site built), the real pipeline
      from empty (10 ran including a routing night, then 0 ran / 10 skipped;
      10 fresh; 7 of 7 snapshots, 10 of 10 stages; gate green; site built),
      with counts and timings in the payload; every provider data-file
      digest and every curated and public digest equal to the references,
      the matrix's included. *(Met with one qualification, on the owner's
      word: Geofabrik's 404 stopped the first run, so the OpenStreetMap
      extract's snapshot was copied from the working clone, verified
      against its manifest and its MD5 pin; the six other providers were
      fetched fresh.)*
- [x] Baselines recorded in the payload and appended to "Resource
      baselines", compared with the budgets, peak RSS included.
- [x] CI on EP-16a's commit recorded, green on Windows and Linux or its
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

## Handoff payload (filled 2026-11-27)
- **Packet:** EP-16b, done at `HASH` (recorded in the README row by the
  commit that follows it). Planning Baseline v1.0. No code changed.
- **What the session did, in order.** Read first (OT-1 ticked by the
  owner; no open inbox message). Confirmed the push (the remote's `main`
  is `fa423e0`) and read CI and Dependabot (below). Cloned `main` at
  `fa423e0` into the session's scratchpad (`git clone -c
  core.longpaths=true`), synced it, installed and checked the toolchain,
  ran the suite and the fixture verbs, then the real pipeline from an empty
  data root under a keep-awake request: a scratch wrapper holding the same
  per-process `SetThreadExecutionState` request as `route matrix
  --keep-awake`, while the machine's power plan also has sleep and
  hibernation off. The first run stopped in `acquire` on Geofabrik's 404
  (the brief's stop); the facts were checked and the decisions put to the
  owner; on the owner's word the pinned snapshot was seeded and the run
  repeated, the night attended and read with `route status` while it ran.
  Then the second run and the verbs, the digest comparison (a
  standard-library script in the scratchpad, run through `uv run
  --project`, matching every digest quoted in the EP-8b, EP-10, EP-12 and
  EP-15 handoffs, so no digest was typed), the baselines, and the scratch
  clone deleted.
- **The stop: refresh drift on one of the seven providers.** Geofabrik no
  longer serves `pennsylvania-260831.osm.pbf`. In the first run's `acquire`
  (2026-11-27 04:30Z) attempt 1 hit the 60 s read timeout and attempt 2 got
  HTTP 404; the stage failed after 95 s, its staging discarded, nothing
  installed. Checked by hand at 04:35Z: the URL answers 301 to
  `download.geofabrik.de/north-america/us/pennsylvania/pennsylvania-260831.osm.pbf`,
  which is 404, and the sidecar is gone the same way. That folder listed
  the 1 January extract of every year from 2014 to 2026, the first-of-month
  extracts of 2026-09-01, 10-01 and 11-01, and the daily ones of 2026-11-20
  to 11-26 (observed; no documented policy was read). The region page, the
  snapshot's terms archive, now redirects to `…/pennsylvania/index.html`
  and still carries both checked phrases. The fetches before the failure
  matched: ACS and CenPop at the pinned byte counts, SEPTA's GTFS against
  its pinned SHA-256.
- **Owner decisions (2026-11-27 UTC, through `AskUserQuestion`, one per
  decision; every answer the recommended option) and their outcomes.**
  1. *The stop:* finish on the pinned bytes. The working clone's
     `raw/osm_network/2026-09-03/` (four files) was copied into the empty
     raw zone (0.2 s); `phillysim verify --raw` passed it and its MD5 is
     `a779d2ef14c8addce6eac207ab9cd851`, ADR-0008's pin; `acquire` verified
     it against its manifest and re-used it (its own path for a snapshot
     already present; it has no per-source switch) and fetched the other
     six fresh. The equality of that one file is therefore by
     construction, not a fresh acquisition.
  2. *The controlled refresh:* planned in EP-17, through EP-16f's brief
     note, beside the deferred runtime upgrades, so that the references are
     re-recorded once. Applied in the note, with the facts above.
  3. *Pull request #12* (virtualenv 21.14.13), still open 14 minutes after
     the push: closed by hand with a one-line comment (04:40:44Z).
  4. *The four pull requests opened after the push* (#17 `setup-uv`
     10.4.0, #18 ruff 0.17.6, #19 playwright 1.65.2, #20 duckdb 2.0.1,
     which replaced #8): noted, no change. #20 joins #6 and #7 in EP-16f's
     note; #17 to #19 wait for the next checkpoint's triage.
  5. *The plan digest's line endings* (below): to EP-17's inputs, through
     EP-16f's note.
  6. *The redirected-output crash of `route verdict`* (below): EP-16d
     writes the `PYTHONUTF8=1` note into the package README; the code fix
     goes to EP-17's inputs.
  The commits are under the autopilot (the owner's standing yes, crw
  D-22); the push is the owner's.
- **Commands and results (the fresh clone; each timed).**

  | Step | Result | Time |
  |---|---|---|
  | `uv sync --locked --group routing` | `.venv` 762 MB | 16.1 s |
  | `phillysim toolchain install` / `check` | JDK and jar digests equal to the pins; four checks ok | 9.4 s / 1.4 s |
  | `uv run pytest` | **664 passed, 3 skipped** (the manual real-data-root tests) | 187 s |
  | `run --fixture`, twice | 11 ran; then 0 ran, 11 skipped | 2.3 s, 1.5 s |
  | `status --fixture`, `verify --fixture` | 11 fresh; 8 of 8 snapshots, 11 of 11 stages | 1.4 s, 1.3 s |
  | `gate --fixture`, `site build --fixture` | green, 5 files Bucket B, 8 sources; `county_boundary (1)` | 1.3 s, 1.6 s |
  | `phillysim run` (first) | `acquire` failed on the 404; recorded incomplete | 95 s |
  | `phillysim run` (the seeded snapshot) | **10 ran**, the night among them | 1,218 s |
  | `phillysim run` again | **0 ran, 10 skipped** | 6.1 s |
  | `status`, `verify` | 10 fresh; **7 of 7 snapshots, 10 of 10 stages** | 2.2 s, 1.8 s |
  | `gate`, `site build` | green, 5 files Bucket A (CC-BY-4.0), 4 sources; `county_boundary (1), roads (426)` | 1.2 s, 1.8 s |
  | `route status` | the night finished, peak 5.32 GB | 1.2 s |
  | `route verdict --night 20261127T044506Z-travel-times` | wall, RSS and walk+transit finite pairs **pass**; walk finite pairs the owner's reading (46.95 % against the 56.24 % reach bound); determinism pending (the stage's plan has no repeat runs; the cross-clone repeat is the comparison below); hand check and concordance pending by design | 1.3 s |

  Working clone: `pre-commit run --all-files` and the diff scan (below).
- **Digest comparison against the working clone and the handoffs: 56 of
  57 judged items equal, the one difference outside the brief's criteria.**
  Equal: the nine provider data files of the seven manifests (ACS
  `38d1a992…` and `2f64e698…`, CenPop `c5c3feea…`, GTFS `4d3fa20e…`, the
  OSM extract `9dded6c9…` and its MD5 sidecar, SNAP `872a6f81…`, roads
  `b0f60f79…`, tracts `818bdadf…`) and the extract's MD5; each manifest's
  nine other fields (source, snapshot ID, schema, synthetic, bucket,
  license note, both URLs, terms archive); the clip `1f87cacb…`, the two
  feed zips and `acs_tracts.parquet`; the five curated tables; the six
  public files; both core runs' canonicalized-value and byte digests and
  row counts against **both** recorded nights (`100625cd…` / `8b34f3f0…`
  walk, `e35b466d…` / `30ef00d7…` transit); the curated matrix's value
  digest `fc50873d…` (also recomputed from the file with
  `records.canonical_value_digest`), byte digest `f2ed818a…` and its
  1,312,944 rows; the stage's input and points digests. 36 of the equal
  items also match a digest quoted in a handoff. **The difference:** the
  stage's recorded plan digest, `e5761e61…` here against `9ba23f68…`. Git
  stores `plans/travel-times.json` with LF, the fresh clone checked it out
  with CRLF (`core.autocrlf=true`; 1,913 B against 1,849 B), and the stage
  digests the raw bytes; a finding, carried to EP-17. Shown, not judged:
  the archived terms pages, which differ per fetch as recorded since EP-5a
  (the SNAP data page too this time, 43,072 B against EP-10's 44,082 B,
  its as-of sentence intact), and the JSON reports, five of seven
  byte-equal and the other two differing in timings and the night's ID.
- **CI on EP-16a's pushed commit.** Run 45939483634 on `fa423e0`: green on
  both platforms (ubuntu 92 s, windows 149 s; the durations are in the
  baselines).
- **Dependabot after the push.** The 35 alerts on `phillysim/uv.lock`
  (numbers 10 to 44) read fixed (2026-11-27 04:22Z). Dependabot closed #10,
  #11, #13, #14 and #15 within two minutes of the push; #12 stayed open
  and was closed by hand (decision 3). It also closed #8 (duckdb 1.5.6),
  replaced by #20 (duckdb 2.0.1), and opened #17 to #19; #6 and #7 stay
  open as deferred.
- **Resource observations** (the table is in `phillysim/README.md`,
  "Resource baselines", EP-16b block; every number within budget). The
  real run 1,218 s, the night's core wall 963.8 s (3.3 % of 8 h; walk
  115.6 s with r5py's network built cold, transit 848.2 s; the two
  recorded nights took 829.9 s and 885.6 s). Peak process-tree RSS per run
  5.05 GB walk and 5.32 GB transit (26.6 % of the 20 GB budget); over the
  whole `run` tree 5.73 GB (the `network` clip 3.57 GB, sampled from 76 s
  in), the first non-routing peak measured. Data root 1.16 GB (r5py's cache
  526 MB, raw 491 MB); the clone 2.36 GB in all; the public zone 331,050 B
  gzipped. Network: 145 MB from six providers, the JDK and jar 270 MB; the
  wheels came from uv's warm cache (the sync took 16 s; whether uv
  reached PyPI at all was not checked).
- **Files changed (documentation only).** `phillysim/README.md`
  ("Resource baselines": the EP-16b block); `CHANGELOG.md` (Unreleased,
  Changed); `roadmap/README.md` (the EP-16b row; EP-16b's brief note
  removed; notes for EP-16c to EP-16f); this brief; `roadmap/owner-tasks.md`
  (the owner's tick of OT-1, committed with this brief).
- **Unresolved risks / questions.** (1) Until the refresh lands (EP-17), no
  fresh clone can run the real pipeline: `acquire` stops at
  `osm_network`, and nobody can reproduce the routing inputs from the
  providers. (2) Geofabrik's retention is as observed, not documented: how
  long a first-of-month extract stays is unknown, while the 1 January
  files went back to 2014. (3) A failing fetch through the redirect spends
  a 60 s read timeout before the 404 (cosmetic). (4) EP-17 re-records the
  references for both the refresh and the deferred upgrades (#6, #7, #20),
  so the digests confirmed here are the last on the present pins. (5)
  EP-8b's and EP-12's handoffs abbreviate `public/sites.csv`'s digest as
  `ea3bdea9…f1a3`, a typo for `…a1a3`: the file equals EP-7's full
  reference, and the frozen payloads are left as they are. (6) The
  whole-run peak came from a scratch sampler; the project samples only the
  routing children, so a later checkpoint that wants the non-routing peak
  measures it the same way.
- **No-go areas touched:** none. No code; no re-pin; no dependency change;
  the working clone's data root read only (the seeded snapshot copied out
  of it); nothing written under a tracked `public/` zone or `site/dist/`;
  GitHub written only as the owner named (#12); no machine identifier or
  absolute path in a tracked file (the diff scanned); the scratch clone
  deleted with its data root, toolchain and caches.
- **`roadmap/README.md`:** the EP-16b row `☑ HASH`.
- **Exact next packet: EP-16c**, the license-label sweep with the
  data-facing documents.

> **Completion note (2026-11-27; claude-opus-5-5/max; ≈ 80 min over two
> sittings).** The fresh clone of `main` re-ran green, fixture and real,
> and every provider data file, curated table, public file and matrix
> digest equals the references; the new night repeats both recorded
> nights' core-run digests across clones. The run's first step stopped the
> brief: Geofabrik no longer serves the pinned OpenStreetMap extract (404
> after a move into per-region folders). Owner decisions, each the
> recommended option: finish the re-run on the working clone's verified
> copy of that snapshot (done; the six other providers fetched fresh);
> plan the controlled refresh in EP-17 through EP-16f's note; close
> Dependabot's #12 by hand (done); note #17 to #20 with no change; carry
> the plan digest's line-ending dependence to EP-17; have EP-16d document
> `PYTHONUTF8=1` for the routing verbs' redirected output, the code fix to
> EP-17. Baselines appended, peak RSS included (5.32 GB per run, 5.73 GB
> for the whole run). Commits under the autopilot; the push is the
> owner's. Routine choices: the scratchpad as the clone's place; a
> keep-awake wrapper and a whole-tree RSS sampler, both scratch scripts;
> the comparison widened to the stage's records and the EP-10 handoff.
> The sittings were 04:19 to 05:01 UTC and 07:36 to the commit, with a
> pause for the usage limit between; the routing night took 16 minutes of
> the first. The effort is the launch's suggestion; the panel's setting is
> not visible to the session. The handoff payload above is the detailed
> record.
