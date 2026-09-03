# EP-14 — The pre-scripted run matrix and the first unattended night

**Status:** [ ] planned · **Milestone:** M3 · **Effort:** S (1 session, medium confidence) · **Parallel with:** —

## Outcome & value
The spike's runs are written down as data before they run, and then run
without anyone watching: a plan file that names every run the criteria
need (destination set, mode, walking speed, window, dates, percentiles,
origins), a `route matrix` verb that executes the plan run by run under
EP-13's harness, resumes after a crash at the next incomplete run, records
every number the verdict needs, and writes the outcome code; a rehearsal
on the six-sample-tract subset to check the plan and to extrapolate the
night; and the first unattended night launched at the end of the session
with the owner's word. The unattended time is outside the session box
(milestones.md "Spikes & gates"); the verdict is EP-15's.

## Scope
- in:
  1. **The plan** (`phillysim/src/phillysim/routing/plans/m3-spike.json`,
     tracked; the parameters of ADR-0008 and methodology.md "Travel model"
     verbatim). Origins: the 408 spine centers (`centroid_lon` /
     `centroid_lat`, the CenPop population-weighted centers; the
     block-group sensitivity is M5's). Destinations: **all 1,609 rows of
     `curated/snap_retailers.parquet`** (the supermarket-format 164 are a
     subset, so one run serves both the headline layer and M5's
     all-retailer SRAM variant; R5's cost is in origins and departures,
     not destinations). `max_time` 120 min (the censor); percentiles 50
     and 85; `snap_to_network` on. Runs:

     | Run | Mode | Walk speed | Window | Departures | Role |
     |---|---|---|---|---|---|
     | `walk-48-wed` | walk | 4.8 km/h | (time-invariant; one departure) | 1 | **core** |
     | `transit-48-wed` | walk+transit | 4.8 km/h | Wednesday 2026-09-23, 08:00–20:00 | 720 | **core** |
     | `transit-48-wed-repeat` | walk+transit | 4.8 km/h | as above | 720 | determinism repeat of the core transit run |
     | `walk-30-wed` | walk | 3.0 km/h | one departure | 1 | slow-walk sensitivity |
     | `transit-30-wed` | walk+transit | 3.0 km/h | Wednesday 2026-09-23, 08:00–20:00 | 720 | slow-walk sensitivity |
     | `transit-48-sat` | walk+transit | 4.8 km/h | Saturday 2026-09-26, 08:00–20:00 | 720 | Saturday window (market metrics, M4/M5; timing rehearsal here) |

     The **≤ 8 h wall criterion applies to the two core runs together**
     (`walk-48-wed` + `transit-48-wed`; owner decision at EP-11, question
     4); the repeat and the three sensitivity runs are executed the same
     night, timed, and reported for OQ-C and for M5's planning, and their
     wall is not a kill criterion. The walk run is repeated too
     (`walk-48-wed-repeat`, seconds) so both modes have a repeat.
  2. **`phillysim route matrix --plan FILE [--only RUN] [--origins-subset N]`.**
     Executes the plan in order, one run per child process under the
     sampler (EP-13), one run record each under `runs/routing/<night-id>/
     <run>/` plus a night-level `night.json` (order, per-run outcome, wall
     per run, the core wall, the peak RSS over the night, the outcome
     code); a run already `completed` in the night directory is skipped
     on re-invocation (resume); `killed-rss` on any core run, or a core
     wall over 8 h, marks the night `KILLED-BY-EVIDENCE` in `night.json`
     and continues the remaining runs only if the owner-set flag
     `--continue-after-kill` was given (default: stop, so the evidence is
     the run, not the recovery). The output of each run is the matrix in
     the dictionary's shape (`origin_geoid`, `site_id`, `mode`,
     `time_median_min`, `time_p85_min`, censored at 120; `mode` values
     `walk` / `walk_transit` with the speed and window in the record, not
     the table), as Parquet, plus its canonicalized-value digest (rows
     sorted by key, integer minutes, hashed) and its byte digest. Sanity
     counts computed at the end of each run and written to the record:
     share of finite pairs (methodology.md: ≥ 95 % is the gate), pairs at
     the censor, distribution summary.
  3. **The rehearsal.** `route matrix --plan m3-spike.json
     --origins-subset 6` on the six sample tracts' origins (the same GEOIDs
     as the CI samples) against all 1,609 destinations: proves the plan
     end to end, gives per-origin seconds for each run, and the
     extrapolation to 408 origins written into the handoff and into
     `night.json` as `expected_wall`. If the extrapolated core wall exceeds
     8 h, say so to the owner before launching (not a kill yet: the
     criterion is measured on the full run).
  4. **Launch the night** with the owner's decision (interactive prompt):
     `route matrix --plan m3-spike.json` detached (`Start-Process`,
     logged), the machine left on, the data root as the working area;
     the session ends after the launch is confirmed running and the
     handoff written. The night's records are EP-15's input.
- out (explicit non-scope): the verdict and the hand check (EP-15);
  block-group origins, the threshold grid, farmers' markets or meal sites
  (M4, M5); publishing anything; registering `travel_times` in the real
  pipeline (EP-15 on go); a second night (EP-15 decides whether one is
  needed).

## Prerequisites & locked decisions
- prerequisites: EP-13 (toolchain, sampler, records, smoke green), EP-12.
- locked decisions honored: milestones.md M3 row and "Spikes & gates"
  (pre-scripted matrix; unattended overnight outside the box;
  KILLED-BY-EVIDENCE versus TIMEBOX-EXHAUSTED); methodology.md "Travel
  model" (4.8 km/h and the 3.0 km/h sensitivity; the pinned Wednesday
  08:00–20:00 at one departure per minute; median and 85th percentile;
  the Saturday window; censor at 120), "Units and origins" (the 408
  CenPop centers); architecture.md budgets (20 GB / 22 GB, ≤ 8
  processors, unattended runs accounted separately); ADR-0007 (origins
  and destinations leave the analysis CRS as WGS 84 only at the r5py
  boundary; the matrix carries keys, not geometry); ADR-0008 (dates,
  band, tolerance); the data dictionary's travel-time matrix shape.
- dependencies: none outside the machine (the sources and toolchain are
  installed; no network).

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the unattended run writes
only under the data root (`runs/routing/`, `cache/r5py/`) and never under
`raw/`, `public/`, or `site/`; the sampler's 22 GB kill is armed for every
child; the plan file carries no path, only names and parameters; run
records scrub the data root; the launch is the owner's decision, recorded;
the machine's other work is not touched (no system setting changed; sleep
prevention, if needed, is a documented per-launch step, not a setting);
the matrix tables are Bucket B by derivation (the `osm_network` snapshot
is among their inputs) and stay in the gitignored data root; nothing is
published.

## Likely components & contracts (proposed)
`src/phillysim/routing/{plan,matrix}.py`, `routing/plans/m3-spike.json`,
`cli.py` (`route matrix`), `tests/test_routing_plan.py` (the plan parses,
every parameter equals ADR-0008's, the run list is as above),
`tests/test_matrix_driver.py` (resume, kill handling, outcome code, and
the sanity counts on a fake child that writes crafted matrices; no JVM),
`docs/data-dictionary.md` (`night.json`; the matrix table's `mode`
values and the record's speed / window fields), `phillysim/README.md`
(the verb and the plan), `CHANGELOG.md`, this file. Contract: a run's
output equals the dictionary's travel-time matrix shape; the night record
has the fields the verdict reads (listed in EP-15).

## Implementation notes
Keep the driver free of r5py: it launches EP-13's child per run and reads
records. Build origins and destinations once from the curated tables (the
spine's centers as WGS 84 points; the retailer layer's `longitude` /
`latitude`) and pass them to the child as a Parquet file under the night
directory so every run routes the same points. The transit runs set
`departure` to 2026-09-23 08:00 local (Saturday: 2026-09-26) and
`departure_time_window` to 12 h; the walk runs need no window (set one
minute). Read `feed_info.txt` dates from the unwrapped feeds and refuse a
plan whose dates fall outside either feed's authoritative window. The
rehearsal is the same driver with `--origins-subset`. Extrapolate
linearly in origins and say so. For the launch, a detached process on
Windows (`Start-Process -WindowStyle Hidden`, or `pythonw`) with the
log under the night directory; record the command in the handoff (the
data root scrubbed). If r5py's cache expiry could rebuild the network
mid-night, touch the cache before launch (EP-13 recorded the build cost).

## Acceptance criteria & evidence
- [ ] The plan file exists, is tested against ADR-0008's parameters, and
      lists the runs above with the two core runs first.
- [ ] `route matrix` resumes, records, kills, and codes as specified on a
      fake child (tests); `uv run pytest` green; CI green (no JVM).
- [ ] The rehearsal completed for every run on six origins with records,
      sanity counts, and an extrapolated core wall in the handoff and in
      `night.json`.
- [ ] The night was launched with the owner's decision recorded, is
      running at session end, and its night directory exists with
      `night.json` in state `running`.
- Evidence: the rehearsal's records; the launch log; CI.

## Tests / validation
`uv run pytest`; `pre-commit run --all-files`; the rehearsal by hand;
the launch by hand with `phillysim route status --night <id>` (a small
read-only verb: which runs are done, their wall so far, the last RSS
sample) confirming it is running; a scan of the diff for paths.

## Resource budget
Attended: the rehearsal, minutes to tens of minutes. Unattended: the
night; its wall is the measurement (core ≤ 8 h is the criterion; six
runs plus repeats may take longer and that is recorded, not judged).
RAM: the JVM at 12 GB heap; the sampler reports. Disk: six matrices of
408 × 1,609 rows (about 660,000 rows each, single-digit megabytes) plus
records and logs; the r5py cache; well under 50 GB. Session: one.

## Risks, rollback, stop condition
Rehearsal extrapolates the core wall well over 8 h → say so to the owner
before launching; launch anyway only on the owner's word (the criterion
is measured, not extrapolated), or trim the plan to the core runs. A core
run is killed at 22 GB in the rehearsal → **stop**; that is evidence for
EP-15 to weigh (a rehearsal kill on six origins means the network build,
not the routing, is the problem; ADR-0008's fallback extent is the whole
state extract in the other direction, so the remedy is a smaller buffer
or a kill verdict, both the owner's). The feed's authoritative window
does not contain the pinned dates → **stop**; the dates are ADR-0008's
and change with the owner. The machine sleeps or reboots during the
night → the driver resumes on re-invocation; record the interruption;
the wall criterion counts the run's own wall, not the gap. Rollback:
delete the night directory; nothing else changed.

## Documentation / ADR updates
`phillysim/README.md` (verb, plan, how to launch and resume a night),
`docs/data-dictionary.md` (night record), CHANGELOG, the packet row.
ADR-0008 referenced.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- the rehearsal's per-run wall and per-origin seconds, sanity counts,
  peak RSS; the extrapolated core wall; the launch command (scrubbed) and
  time; the owner's launch decision
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated to `[x] <commit>`
- exact next packet: EP-15 (the verdict), to start only after the night's
  `night.json` reads `finished` (or `KILLED-BY-EVIDENCE`)
