# EP-14 — The pre-scripted run matrix and the first unattended night

**Status:** [x] b35370d done 2026-09-03 · **Milestone:** M3 · **Effort:** S (1 session, medium confidence) · **Parallel with:** —

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
- [x] The plan file exists, is tested against ADR-0008's parameters, and
      lists the runs above with the two core runs first.
- [x] `route matrix` resumes, records, kills, and codes as specified on a
      fake child (tests); `uv run pytest` green; CI green (no JVM).
- [x] The rehearsal completed for every run on six origins with records,
      sanity counts, and an extrapolated core wall in the handoff and in
      `night.json`.
- [x] The night was launched with the owner's decision recorded, is
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

## Handoff payload (filled 2026-09-03)
- **Packet:** EP-14 — done at commit `b35370d` (the work commit `5fc052a`
  plus `b35370d`, which lets a night directory hold a detached launch's
  redirected streams; + this status commit), 2026-09-03, one session, at
  the S estimate; Planning Baseline v1.0. CI run [33813751959](https://github.com/willtfarrington/phillysim/actions/runs/33813751959) on `b35370d` green on `ubuntu-latest` and `windows-latest` (ubuntu 80 s, windows 127 s; 631 passed, 3 skipped on both, without the routing group); the work commit's run 33813523236 green too. Owner review at the
  end of this payload.
- **Files changed.** New: `phillysim/src/phillysim/routing/plan.py` (matrix
  plans), `phillysim/src/phillysim/routing/matrix.py` (the night driver),
  `phillysim/src/phillysim/routing/plans/m3-spike.json` (the plan, tracked),
  `tests/test_routing_plan.py`, `tests/test_matrix_driver.py`. Changed:
  `routing/records.py` (`RunPlan.snap_to_network`, default off so EP-13's
  smoke plan and digests are unchanged), `routing/harness.py`
  (`snap_to_network` passed to r5py; `run(..., run_dir=)`), `cli.py`
  (`route matrix`, `route status`), `phillysim/README.md` (the verb, the
  plan, launch and resume, the rehearsal in the baselines table),
  `docs/data-dictionary.md` (the night record; the matrix's `mode` values
  and where the speed and window live; `plan.json`'s new field),
  `CHANGELOG.md`, `roadmap/README.md` (the packet row), this file.
- **Commands/tests run + results.** `uv run pytest` → **631 passed,
  3 skipped** in 62 s (583 before; 48 new tests, none touching a JVM: the
  driver runs on scripted children through the real `harness.run`, the plan
  tests on crafted tables and feed zips); `ruff check` / `ruff format
  --check` clean; `pre-commit run --all-files` all hooks passed; the packaged
  plan resolved against the real tables and feeds without a JVM (408 origins,
  1,609 destinations; `feed_info.txt`: bus 2026-09-06..2027-02-20, rail
  2026-09-06..2026-10-17, both `v202609060`; no date outside either window);
  `phillysim toolchain check` all four ok; `phillysim status` 9 fresh after
  the rehearsal; the diff scanned for absolute paths, user names, and machine
  identifiers → none; `git ls-files` shows nothing under `data/`.
- **The plan** (`m3-spike.json`, sha256 `febe2614…`): the seven runs of the
  brief's table in order (`walk-48-wed`, `transit-48-wed` core;
  `walk-48-wed-repeat`, `transit-48-wed-repeat`; `walk-30-wed`,
  `transit-30-wed`; `transit-48-sat`), ADR-0008's parameters verbatim
  (America/New_York; 2026-09-23 and 2026-09-26 from 08:00; 720 departures
  for transit, one for walk; percentiles 50 and 85; `max_time` 120;
  `snap_to_network` on; the 408 spine centers; all 1,609 retailers;
  `core_wall_limit_hours` 8), `rehearsal_origins` = the six CI sample
  tracts, and no path anywhere (tested). One departure for the walk runs is
  a one-minute window, which r5py flags with its below-five-minutes warning
  in `log.txt` (harmless; the same as EP-13's `--single-departure`).
- **The rehearsal** (`route matrix --plan m3-spike.json --origins-subset
  6`; night `20260903T222152Z-m3-spike-subset6`, 22:21:52Z–22:23:19Z; the
  six sample tracts × 1,609 retailers; the network from r5py's cache in
  every run). All seven runs `completed`; **86 s of wall together**; core
  wall **24.4 s**; **peak RSS 3.53 GB** (`transit-48-wed`); no sample near
  the 20 GB budget or the 22 GB kill; nothing missing from any grid
  (9,654 rows each, no unsnapped point).
  | run | wall | peak RSS | import / build / route | finite pairs | typical time (finite): p50, max | matrix values digest |
  |---|---|---|---|---|---|---|
  | `walk-48-wed` | 6.9 s | 2.99 GB | 2 / 2 / 2 s | 64.25 % (3,429 over the censor) | 71, 119 min | `3826ed39…` |
  | `transit-48-wed` | 17.4 s | 3.53 GB | 1 / 3 / 12 s | 100 % | 36, 90 min | `ce751261…` |
  | `walk-48-wed-repeat` | 6.9 s | 2.95 GB | 2 / 2 / 2 s | 64.25 % | as above | `3826ed39…` (= original; byte digest equal too) |
  | `transit-48-wed-repeat` | 17.4 s | 3.41 GB | 2 / 2 / 13 s | 100 % | as above | `ce751261…` (= original; byte digest equal too) |
  | `walk-30-wed` | 6.4 s | 2.72 GB | 1 / 3 / 1 s | 35.19 % (6,228 over) | 83, 119 min | `0e7a3b24…` |
  | `transit-30-wed` | 16.2 s | 3.13 GB | 1 / 3 / 11 s | 100 % | 41, 97 min | `c5dde41f…` |
  | `transit-48-sat` | 15.1 s | 3.36 GB | 2 / 2 / 10 s | 100 % | 39, 90 min | `f7318a68…` |
  Per-origin routing seconds: walk 0.33 (4.8 km/h) and 0.17 (3.0 km/h);
  transit 1.67–2.17. The p85 − median mean is 3.5–4.4 min on the transit
  runs and 0 on walk (time-invariant). A plausibility spot check from tract
  `42101000101`: the five nearest retailers (0.2–1 km) route in 2–13 min on
  foot; the three farthest (22–23 km) are censored on foot and 74–79 min
  typical by transit. **Extrapolation** (`expected_wall`, linear in
  origins: fixed import + build cost plus per-origin routing seconds × 408):
  core **960 s = 0.27 h** (walk 140 s, transit 820 s), all seven runs
  3,496 s = 0.97 h; pessimistic, because six origins under-use R5's eight
  threads (the night's first core run then took 54 s against the 140 s
  extrapolated). Well within the 8 h criterion; the owner was told before
  the launch.
- **The launch** (owner decision, question 1 below). First attempt
  22:33:03Z from `phillysim/`: refused by the driver's own empty-directory
  check, because `Start-Process` creates the redirected `launch.log` /
  `launch.err` inside the pre-created night directory before the driver
  starts (the README's own procedure); fixed in `b35370d` (`launch.*` files
  are allowed in a fresh night directory, tested), the refused directory
  (two launch files, no record) deleted, the fix committed and pushed
  before relaunching so the night runs on committed code. Second launch
  **22:36:07Z**, night **`20260903T223607Z-m3-spike`**, the command (data
  root scrubbed):
  ```
  Start-Process -WindowStyle Hidden -PassThru -FilePath .\.venv\Scripts\python.exe `
    -ArgumentList "-m","phillysim.cli","route","matrix","--plan","m3-spike.json","--night","20260903T223607Z-m3-spike","--keep-awake" `
    -RedirectStandardOutput <data-root>\runs\routing\20260903T223607Z-m3-spike\launch.log `
    -RedirectStandardError  <data-root>\runs\routing\20260903T223607Z-m3-spike\launch.err
  ```
  `launch.log`: preflight green (420 GB free, 68.1 GB RAM, the toolchain
  checks), `keep awake: requested`, `night … starting plan m3-spike
  (m3-spike.json febe26143044), 408 origins x 1609 destinations, 7 runs`.
  `route status --night 20260903T223607Z-m3-spike` at 22:38Z: **state
  `running`, driver pid alive**, `walk-48-wed` **completed in 54 s at a
  peak RSS of 5.31 GB**, `transit-48-wed` running; and again at the end of
  the session (below). Sleep prevention: the machine's plan already never
  sleeps on AC (checked with `powercfg`, nothing changed); `--keep-awake`
  is a per-process request released at exit. The night's records are
  EP-15's input; the driver resumes with the same `--night` if the machine
  restarts.
- **Resource observations:** one session, at the S estimate. Attended
  routing: the rehearsal 86 s; the launch seconds. Unattended: about an
  hour expected for all seven runs. RAM: the rehearsal peaked at 3.53 GB;
  the night's first run (408 origins, walk) at **5.31 GB**, so RSS grows
  with the origin count (R5's per-origin result buffers) but stays far
  under the 20 GB budget. Disk: a rehearsal run directory about 0.8 MB
  (`plan.json` 181 KB with the 1,615 points inline, `travel_times.csv`
  519 KB, the Parquet 46 KB); the night's matrices will be about 660,000
  rows each. Suite +48 tests, about +20 s (the scripted children are real
  subprocesses). Network: none (a push and CI).
- **Decisions made (routine, agent's call, logged):** a night lives under
  `runs/routing/<UTC>-<plan>[-subsetN]/` and each run's record under
  `<night>/<run>/` with `run_id` `<night-id>/<run>` (the harness gained a
  `run_dir` override; `records.list_runs` still lists night directories,
  and `matrix.list_nights` filters on `night.json`); the origins and
  destinations are written once to `points.parquet` and every run's
  `plan.json` also carries them inline (the EP-13 child contract; 181 KB
  per run); the harness's raw CSV is kept beside the Parquet, and the
  Parquet is the full origin × destination grid with missing or over-censor
  pairs at 120 (the dictionary's "censored at 120"), sorted by key, with
  byte and canonicalized-value digests over (`origin_geoid`, `site_id`,
  `mode`); "finite" = typical time under 120 (EP-15's reading), computed on
  the raw CSV before censoring; an earlier attempt of a run is kept as
  `<run>.attempt<N>/`; a `failed` / `cancelled` run stops the night in
  state `stopped` (the brief names no behaviour; resuming re-runs it); a
  killed non-core run is recorded and the night continues; `outcome_code`
  holds only `KILLED-BY-EVIDENCE` (`go` and `TIMEBOX-EXHAUSTED` are
  EP-15's); `--origins-subset N` takes the first N of an origin order that
  puts the plan's `rehearsal_origins` first, so N = 6 is exactly the CI
  sample set; the extrapolation is linear in origins with the import and
  build phases as a fixed cost (phase stamps are at second resolution);
  `route matrix` exits 0 only when the night `finished`; `--keep-awake`
  via `SetThreadExecutionState`; r5py's cache files are touched at night
  start (regular files only, see below); the driver's `driver.log` is
  UTC-stamped and appended across invocations; `night.json` is canonical
  JSON (sorted keys), so readers sort `runs` by `order`. **Owner-level
  decisions** below.
- **Two preconditions wobbled and were closed by code.** (1) The
  rehearsal's cache touch followed r5py's three input symlinks (Windows has
  no `follow_symlinks` for `os.utime`) and refreshed the **modification
  times** of the three files under `intermediate/network/`; contents and
  digests unchanged, `phillysim status` 9 fresh, nothing under `raw/`,
  `public/`, or `site/`; the driver now skips symlinks (tested). (2) The
  first launch refused, above. Also noted: `log.txt` (the child's raw
  stderr, EP-13's design) carries r5py's warning with the venv path; the
  JSON records are scrubbed; everything stays under the gitignored data
  root.
- **Unresolved risks / questions (EP-15's inputs):** the **finite-pairs
  gate**: methodology.md's ≥ 95 % finite pairs, read per core run, is met
  by every transit run (100 %) and cannot be met by the walk run over all
  1,609 retailers (64 % at 4.8 km/h, 35 % at 3.0 km/h: a 120-minute walk
  reaches about 9.6 km and the county is over 20 km across); the owner
  chose to record it (question 3) and EP-15 decides whether the gate reads
  per mode or for the walk+transit run only, with the full night's numbers.
  The extrapolation is pessimistic (54 s measured against 140 s); the
  night's own walls are the measurement. RSS grows with origins (5.31 GB
  at 408 walk origins); the transit runs' night peaks are the number EP-15
  reads against the 20 GB budget. If the night's `night.json` ends in
  `stopped` (a failed child), re-invoke with the same `--night`; the
  interruption is recorded and the earlier attempt kept.
- **No-go areas touched:** none (the unattended run writes only under
  `runs/routing/` and `cache/r5py/`, plus the disclosed mtime touch of
  three intermediate files, closed; no system setting changed; nothing
  published; the plan file carries no path; nothing under `data/`
  committed; CI installs no routing group and runs no JVM; no machine
  identifier or absolute path in a tracked file, in `night.json`, or in a
  run record).
- `roadmap/README.md` packet row updated to `[x] b35370d`; the M3 heading
  stays open (EP-15 remains).
- **Exact next packet: EP-15** (`roadmap/EP-15-routing-verdict.md`), to
  start only after `data/runs/routing/20260903T223607Z-m3-spike/night.json`
  reads `finished` (or `KILLED-BY-EVIDENCE`); `uv run phillysim route
  status --night 20260903T223607Z-m3-spike` says which.

### Owner review (2026-09-03)

Three decisions put to the owner interactively; **the recommended option
was accepted for every one**:
- **The launch:** launch the full plan tonight (all seven runs, detached,
  the machine left on), after the rehearsal's extrapolated core wall of
  0.27 h was reported. Applied: launched 22:36:07Z (the first attempt at
  22:33:03Z refused and fixed, above), confirmed running with `route
  status`.
- **Commit, push, CI, status commit:** yes; the work commit before the
  launch so the night runs on committed code, the push after the launch
  was confirmed, the status commit once CI is green. Applied: `5fc052a`,
  `b35370d`, CI run 33813751959 green, then this status commit.
- **The walk finite-pairs finding:** record it as an EP-15 input, no
  change to methodology.md now. Applied: here and in the CHANGELOG.

**At session end (22:40Z):** `route status --night 20260903T223607Z-m3-spike`
→ state `running`, driver alive; `walk-48-wed` completed (54 s, 5.31 GB);
`transit-48-wed` running at 116 s; the other five pending; `night.json`
present in state `running`. One limitation noticed here: the harness writes
a run's `rss.csv` when the run ends, so `route status` shows a running run's
wall so far but its last RSS sample only for completed attempts (writing the
series incrementally is a small later change, not needed for the verdict).
