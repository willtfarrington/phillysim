# EP-15 — The M3 verdict: criteria against the records, the determinism band, the hand check, go or kill, M3 closes

**Status:** [~] in progress (2026-09-03: the mechanical criteria, the concordance, the forty project-side hand-check times, and the `travel_times` stage are done; the planner tally, the outcome code, the M3 close, and the second night wait on the owner, see the handoff) · **Milestone:** M3 · **Effort:** S (1 session, medium confidence) · **Parallel with:** —

## Outcome & value
The routing spike has a verdict with its evidence written down: every
numeric criterion of milestones.md and methodology.md read against the
night's records, the determinism band measured (OQ-C closed by that
number), the hand check against a public trip planner done and tallied,
and one of three outcome codes recorded: **go** (walk+transit within the
budgets; the real pipeline gains its `travel_times` stage, whose first run
is the second unattended night), **KILLED-BY-EVIDENCE** (a criterion
failed with the numbers; the walk-only fallback packet is authored and
becomes the next packet), or **TIMEBOX-EXHAUSTED** (no verdict is
reachable on the records after the one owner-approved extension; same
fallback). The M3 heading in the README closes with the go/no-go evidence,
and the third checkpoint falls due next.

## Scope
- in:
  1. **Read the night** (`runs/routing/<night-id>/night.json` and the run
     records). The criteria, verbatim from the baseline, each with the
     number and pass / fail:
     - **wall ≤ 8 h** for the pre-scripted run matrix (milestones.md M3
       row; applied to the two core runs together, owner decision at
       EP-11);
     - **process-tree RSS ≤ 22 GB** (milestones.md), read as: no core run
       was killed at the 22 GB kill and the night's peak is reported
       against the **20 GB budget** (architecture.md; a peak between 20
       and 22 GB is a pass with a finding);
     - **determinism within band** (milestones.md; AM-2: pinned seeds or a
       documented variance band; quality.md: "checksum-identical within
       the pinned Windows environment; canonicalized-value hashes
       cross-platform"): the core runs and their repeats compared pair by
       pair; the band of ADR-0008: **go** if every pair is identical
       (checksum-identical) **or** at least 99.9 % of pairs are identical
       and no pair differs by more than 1 minute (the departure-minute
       granularity), the observed numbers becoming the documented variance
       band; anything wider is not a pass on this criterion and goes to
       the owner (widen the band with a claims-wording change, or kill);
     - **sanity gates** (methodology.md "Validation"): ≥ 95 % finite
       origin–destination pairs per core run (finite = under the 120-min
       censor); **≥ 80 % of hand-checked OD times within tolerance** (item
       2); **walk-network concordance ρ ≥ 0.95 against the fallback
       engine** (item 3).
  2. **The hand check** (ADR-0008's tolerance; owner decision at EP-11,
     question 3): ten origin–destination pairs chosen by rule (every
     fortieth tract in sorted GEOID order from the first, each paired with
     its nearest supermarket-format retailer by the QA slice; the fifth and
     tenth paired instead with the farthest retailer inside 120 min so the
     long tail is covered), each routed in EP-13's single-departure mode at
     08:30 and 17:30 on the pinned Wednesday for walk and for walk+transit
     (40 checks), and compared by hand against a public trip planner's
     answer for the same points, date, and departure (SEPTA's own planner
     for transit; a general planner for walking), which is a **manual spot
     check, never a data source**: only the tally and the per-check
     difference in minutes are recorded, in this handoff. Tolerance: walk
     within **3 minutes or 15 %** of the planner, whichever is larger;
     walk+transit within **10 minutes or 25 %**, whichever is larger; the
     gate passes at 32 of 40 or more.
  3. **The walk concordance** against the fallback engine: build the
     walk-only network with OSMnx 2.x on the same clipped extract and run
     scipy's sparse Dijkstra (both wheels: `osmnx` 2.1.1, `scipy` 1.18.1,
     resolved 2026-09-03; added to the `routing` group here, not before)
     for the 408 × 164 supermarket-format walk pairs at 4.8 km/h;
     Spearman ρ between the two engines' walk times over finite pairs;
     the gate is ρ ≥ 0.95. This is also the fallback's rehearsal: if the
     verdict is kill, the code stays and the fallback packet grows from it.
  4. **The verdict**, recorded in this file's handoff, in
     `roadmap/open-questions.md` (OQ-C closed with the band), and in
     `roadmap/README.md` (the M3 heading):
     - **go**: register the real pipeline's `travel_times` stage
       (`phillysim.routing.stage`: inputs the spine, the retailer layer,
       and `intermediate/network/`; params the plan's core parameters;
       output `curated/travel_times.parquet` in the dictionary's shape,
       Bucket B by derivation; the body is the matrix driver on the two
       core runs) and launch its first run as the **second unattended
       night** at the end of the session with the owner's word; the
       matrix that run produces is the pipeline's, verified against the
       first night's core digests by the third checkpoint (a carry-in to
       the M5 gate is written in milestones.md). `publish` is untouched,
       so the public zone stays Bucket A until M5 publishes a travel-time
       metric (owner decision at EP-11, question 7).
     - **KILLED-BY-EVIDENCE**: the failing criterion and its number in
       the handoff; the walk-only fallback packet (methodology.md: OSMnx
       2.x + scipy sparse Dijkstra, walk only; scope.md: partial fallback
       permitted, tract-origin transit may ship while block-group
       sensitivity is demoted) is authored from `_TEMPLATE.md` as the next
       free integer and becomes the next packet; the risk table row
       "Routing spike kill" is updated; sources.md and DATA-LICENSES
       record that the SEPTA feed is retained for a v1.x transit attempt
       or deleted (owner's call).
     - **TIMEBOX-EXHAUSTED**: if at the start of this session the night is
       incomplete or its records cannot support a verdict, the session
       first asks the owner for the **one extension** (a further attended
       packet, next free integer, authored in this session, plus one more
       night); if the extension was already used, or declined, the code is
       recorded and the fallback packet authored as above. The verdict
       session calls the code; the owner confirms it (interactive prompt).
  5. **Close M3** in the README (heading status and the go/no-go
     paragraph with the numbers), `milestones.md` (M3 row; the "Estimate
     accuracy" row for M3: packets authored versus the 3-attended estimate;
     the third checkpoint's due point), `CHANGELOG.md`.
- out (explicit non-scope): publishing any travel-time metric or file
  (M5, M6); the block-group sensitivity and the threshold grid (M5);
  changing a criterion, a budget, or the band beyond recording what was
  measured (a change is a baseline change for the owner); executing the
  fallback (its own packet).

## Prerequisites & locked decisions
- prerequisites: EP-14 with its night finished (or killed); EP-13; EP-12.
- locked decisions honored: milestones.md M3 row, "Spikes & gates", and
  the risk table; methodology.md "Validation" and "Travel model";
  architecture.md budgets; quality.md AM-2 wording; scope.md kill
  criteria; ADR-0003 (the matrix is Bucket B); ADR-0006 (the `travel_times`
  stage's parameters are the methods axis); ADR-0008 (band, tolerance,
  dates); docs/CLAIMS.md for every sentence written into the README and
  the cards; the fallback wording (methodology.md, scope.md, milestones.md
  risk table) quoted, not paraphrased.
- dependencies: the night's records on the machine; a public trip planner
  reached by hand in a browser (nothing automated, nothing stored but the
  tally); PyPI for `osmnx` and `scipy` (wheels).

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the trip planner is queried
by a person in a browser for forty checks and nothing from it is stored
as data (no scraping, no automation, no cached responses; the tally and
minute differences only); nothing is published (the public zone's digests
equal the EP-8b references at the end of the session); the `travel_times`
stage, if registered, writes only `curated/travel_times.parquet` and its
report and is Bucket B by derivation; the second night, if launched, is
the owner's decision; the fallback packet, if authored, carries its own
safety preconditions; every number in the README paragraph is traceable
to a record file; no machine identifier or absolute path enters a tracked
file.

## Likely components & contracts (proposed)
`src/phillysim/routing/verdict.py` (reads a night against the criteria
and prints the table; tested on crafted records), `routing/concordance.py`
(the OSMnx + scipy walk engine and Spearman ρ), on go `routing/stage.py`
and `pipeline.py` (the `travel_times` stage, ten stages), `cli.py` (`route
verdict --night ID`, `route handcheck --night ID` printing the forty
project-side times), `pyproject.toml` + `uv.lock` (`osmnx`, `scipy` in the
routing group), `tests/test_verdict.py`, `tests/test_concordance.py` (on
the sample-tract clip, no JVM: the OSMnx side runs in CI on the committed
OSM sample; the r5py side is read from a crafted record),
`docs/data-dictionary.md` (the matrix's first real instance; the stage),
`docs/method-cards/travel-times.md` (a stub naming the engine, pins,
parameters, band, and hand-check result; M5 completes it),
`roadmap/open-questions.md` (OQ-C), `roadmap/README.md` (M3 closes),
`roadmap/milestones.md`, `roadmap/architecture.md` (stage row 9),
`CHANGELOG.md`, and on kill the new fallback packet file with its README
row; this file.

## Implementation notes
Do the verdict table first, mechanically, from the records; only then the
hand check and the concordance, so a KILLED-BY-EVIDENCE on wall or RSS is
known before an hour of planner queries. The determinism comparison is a
join of the core run and its repeat on the key with per-pair differences
in integer minutes; report count identical, share, max difference, and
the distribution; the same for the walk pair. For the concordance, OSMnx
reads the clipped PBF (its `graph_from_xml` path or a conversion through
pyosmium to OSM XML; no network call: `osmnx` must not download
anything, and the test asserts its settings disable that), and Dijkstra
runs on edge lengths at 4.8 km/h from the nearest node of each origin and
destination; keep the comparison over finite pairs and say how many were
excluded. Write the README's M3 paragraph in the claims-matrix register:
what was measured, the numbers, the code, the packet that follows. On go,
the stage's fingerprint covers the two snapshots, the spine, the retailer
layer, and the plan parameters, so a refresh or a parameter change re-runs
routing (an unattended night); say so in `phillysim/README.md`: a fresh
clone's `phillysim run` now includes an overnight stage, and the third
checkpoint's fresh-clone re-run must plan for it (recorded for the
checkpoint's author).

## Acceptance criteria & evidence
- [ ] The verdict table in the handoff: every criterion with its number,
      its source document quoted, and pass / fail; the outcome code
      recorded and confirmed by the owner.
- [ ] OQ-C closed in `open-questions.md` with the measured band (or
      recorded as failed with the numbers); the AM-2 wording in
      quality.md confirmed or amended to the measured band.
- [ ] The hand check tallied (n of 40 within tolerance) and the walk
      concordance ρ recorded, each against its gate.
- [ ] On go: the `travel_times` stage registered and tested on crafted
      inputs without the JVM; the second night launched on the owner's
      word; the M5-gate carry-in written. On kill or time box: the
      fallback packet file exists from the template with its README row,
      and the risk table row is updated.
- [ ] `roadmap/README.md` M3 heading closed with the evidence paragraph;
      `milestones.md` M3 row and "Estimate accuracy" updated; CHANGELOG.
- Evidence: the records; CI green; the owner review in the handoff.

## Tests / validation
`uv run pytest` (the verdict reader and the concordance on crafted and
sample inputs; no JVM in CI); `pre-commit run --all-files`; `route
verdict --night <id>` by hand with the output kept; the forty planner
checks by hand; on go, `phillysim status` showing the new stage `missing`
until its night completes; a scan of the diff for paths and identifiers.

## Resource budget
Attended: the verdict is minutes; the hand check about an hour of a
person's time; the concordance minutes (OSMnx on the clipped extract is
a few hundred megabytes of RAM). Unattended (go): the second night, the
two core runs through the runner. Session: one attended.

## Risks, rollback, stop condition
A criterion fails → not a stop: that is the KILLED-BY-EVIDENCE path,
taken with the owner. Two criteria disagree on the reading (a pass on
wall, a peak between 20 and 22 GB, a band just outside) → the owner
decides, with the options written down; never resolve by default. The
night is incomplete → the TIMEBOX path above. The planner is unreachable
or gives no transit answer for a pair → substitute the next pair by the
same rule and record it; never fabricate a check. Rollback: the verdict
is documentation plus, on go, one stage registration (revertible by
commit; the night's outputs stay in the data root).

## Documentation / ADR updates
`roadmap/README.md` (M3 heading and paragraph; a fallback packet row on
kill), `roadmap/milestones.md` (M3 row, "Estimate accuracy", the risk
table, the M5-gate carry-in on go, "Spikes & gates" checkpoint pointer),
`roadmap/open-questions.md` (OQ-C), `roadmap/quality.md` (AM-2 band
wording), `roadmap/architecture.md` (stage row 9), `docs/data-dictionary.md`,
`docs/method-cards/travel-times.md` (stub), `phillysim/README.md`,
`CHANGELOG.md`; ADR-0008 amended only if a measured number replaces a
provisional one (the band), recorded as an amendment with the date.

## Handoff payload (session 1, 2026-09-03; the packet stays in progress)

- **Packet:** EP-15, `[~]` in progress. Planning Baseline v1.0; roadmap
  as of EP-14's handoff commit `a5076dc`. The session read EP-14's night
  (finished 2026-09-03 23:24:02Z, state `finished`, no outcome code), so
  the TIMEBOX path was not needed and no extension was asked for.
- **Files changed.** Code (`phillysim/`): `src/phillysim/routing/verdict.py`
  (new: the criteria reader, the pair-by-pair determinism comparison, the
  straight-line reach bound, `verdict.json`, `--record`),
  `routing/handcheck.py` (new: the pairs by rule, the two single-departure
  runs, the forty checks, the hand-typed planner file and its tally),
  `routing/concordance.py` (new: the fallback engine on the clip with no
  network call; Spearman ρ), `routing/stage.py` (new: the `travel_times`
  stage) and `routing/plans/travel-times.json` (new: the spike's two core
  runs verbatim), `pipeline.py` (the stage registered between `network`
  and `metrics`; `real_pipeline(routing_runner=, toolchain=,
  routing_check=)` for the suite), `cli.py` (`route verdict`, `route
  handcheck`, `route concordance`), `routing/__init__.py`, `pyproject.toml`
  + `uv.lock` (`osmnx==2.1.1`, `scipy==1.18.1` in the `routing` group;
  `networkx` 3.6.1 comes with osmnx). Tests: `tests/test_verdict.py`,
  `tests/test_handcheck.py`, `tests/test_concordance.py`,
  `tests/test_travel_times_stage.py` (new); `tests/conftest.py` (the sample
  pipeline routes its `travel_times` stage on a scripted child with a
  crafted toolchain record), `tests/test_no_jvm_in_ci.py` (the group's new
  members; the new modules import no JVM), `tests/test_routing_plan.py`
  (both packaged plans), `tests/integration/test_real_pipeline.py` (ten
  stages). Documentation: `docs/method-cards/travel-times.md` (new stub),
  `docs/data-dictionary.md`, `docs/DATA-LICENSES.md`,
  `roadmap/architecture.md` (stage 9), `roadmap/open-questions.md` (OQ-C
  closed), `roadmap/quality.md` (the band as measured),
  `roadmap/adr/0008-routing-toolchain-pins.md` (a measured note, not an
  amendment), `roadmap/milestones.md` (estimate accuracy EP-10 to EP-15 and
  M3; the third checkpoint due as EP-16), `roadmap/README.md` (EP-15 row
  `[~]`; the M3 heading `[~]` with the evidence paragraph), `CHANGELOG.md`,
  `phillysim/README.md` (the stage, the three verbs, the second night's
  launch procedure, resource observations), this file.
- **Commands / tests.** `uv add --group routing osmnx==2.1.1
  scipy==1.18.1`; `uv run ruff check` and `ruff format --check` clean;
  `uv run pytest`: **663 passed, 3 skipped** in about 2 min (the routing
  group installed here, so the OSMnx-side concordance tests ran; they
  skip in CI, which installs no routing group); `pre-commit run
  --all-files` clean; `phillysim route verdict --night
  20260903T223607Z-m3-spike --write` (the table below; `verdict.json`
  written, no code recorded); `phillysim route concordance` (2 min 19 s;
  `concordance/` under the night); `route handcheck` (the two runs under
  `handcheck/`; the forty times below); `phillysim status` on the real root:
  nine stages fresh and **`travel_times` missing**, as the brief's
  evidence asks, until its night runs. **Commits and CI (owner decision 4
  below):** the work commit `7202f43`, pushed; CI run 33828141148 on it
  **failed on both platforms** (one test: `compare()` used pandas'
  `corr(method="spearman")`, which imports scipy, absent in CI where the
  routing group is not installed); fixed in `9638bd2` (Spearman ρ as the
  Pearson correlation of pandas' average ranks; the recorded ρ = 0.993453
  re-computed from the saved fallback table to the same six decimals); CI
  run **33828405482 green** on Windows and Linux (660 passed, 5 skipped
  there: the three OSMnx-side tests and the two `--real-data-root` ones
  skip). The handoff record commit follows.
- **The verdict table** (night `20260903T223607Z-m3-spike`; every number
  from `night.json`, the run records, `concordance.json`, and
  `handcheck.json`; the criteria quoted verbatim in
  `phillysim.routing.verdict.SOURCES`):

  | Criterion (source) | Number | Status |
  |---|---|---|
  | wall ≤ 8 h, the two core runs together (milestones.md M3 row; ADR-0008) | 829.9 s = 0.23 h (walk 54.2 s + walk+transit 775.7 s); 2.9 % of the limit; the seven runs 2,833 s of child walls, 47 min 54 s of night | **pass** |
  | process-tree RSS ≤ 22 GB (milestones.md); peak against the 20 GB budget (architecture.md) | no core run killed; peak 5.39 GB (`transit-48-sat`) = 27.0 % of the budget; no run crossed it | **pass** |
  | determinism within band, `walk-48-wed` vs its repeat (milestones.md; ADR-0008 / OQ-C; quality.md) | 656,472 of 656,472 pairs identical in both columns; max difference 0; byte digests equal (`8b34f3f0…`), value digests equal (`100625cd…`) | **pass** (band measured: zero) |
  | determinism within band, `transit-48-wed` vs its repeat | 656,472 of 656,472 identical; max difference 0; byte (`30ef00d7…`) and value (`e35b466d…`) digests equal | **pass** (band measured: zero) |
  | ≥ 95 % finite pairs, `transit-48-wed` (methodology.md "Validation") | 656,172 of 656,472 = 99.95 % finite (300 at the censor; 0 missing rows; every origin has a finite pair) | **pass** |
  | ≥ 95 % finite pairs, `walk-48-wed` (methodology.md "Validation") | 308,225 of 656,472 = 46.95 % under the 120-min censor; the straight-line reach bound at 4.8 km/h (9.6 km) admits at most 369,178 pairs = 56.24 %, so no engine can meet 95 % for walk over all 1,609 retailers under this censor (the county spans 27 km × 28 km); 83.5 % of the pairs the bound admits are finite; every origin has a finite pair; the fallback engine over the 164 supermarket-format destinations reports 42.5 % finite where R5 reports 43.1 % | **owner reading** (decision 1 below) |
  | walk-network concordance ρ ≥ 0.95 vs the fallback engine (methodology.md) | Spearman ρ = **0.9935** over 28,256 pairs both engines report under the censor, of 66,912 (408 × 164 supermarket-format); excluded: R5-censored only 168, fallback-censored only 550, both 37,938; Pearson r 0.9942; mean absolute difference 1.51 min, median 0.80 min; the fallback is slower by 1.10 min on average (median ratio 1.009); graph 265,006 nodes, 748,296 edges, 41,120 km from 201,525 walkable of 224,252 highway ways | **pass** |
  | ≥ 80 % of hand-checked OD times within tolerance, 32 of 40 (methodology.md; ADR-0008) | the forty project-side times are routed (below); the planner comparison is a person's hour in a browser and has not been done | **pending** (decision 2) |

  Sensitivity and Saturday runs, timed and reported, not judged (M5's
  inputs): `walk-30-wed` 30.5 s, 5.15 GB, 23.09 % finite; `transit-30-wed`
  626.6 s, 5.13 GB, 99.65 % finite; `transit-48-sat` 579.7 s, 5.39 GB,
  99.85 % finite; typical walk+transit times over finite pairs: Wednesday
  4.8 km/h median 52 min (p90 80), 3.0 km/h median 58 (p90 87), Saturday
  median 55 (p90 83).
- **The hand check's forty project-side times** (`route handcheck`;
  `handcheck.json` under the night; the pairs by rule, every fortieth
  tract from the first in sorted GEOID order, 1-based positions 5 and 10
  the farthest supermarket-format retailer under the censor by the core
  walk run, read as the walk-finite retailer with the largest typical
  time, so both modes stay comparable; nothing substituted). Typical
  minutes at 08:30 / 17:30, walk then walk+transit:

  | # | Origin tract → retailer (straight line; core walk) | walk 08:30 / 17:30 | walk+transit 08:30 / 17:30 |
  |---|---|---|---|
  | 1 | 42101000101 → Riverwards Produce (341 m; 6 min) | 6 / 6 | 6 / 6 |
  | 2 | 42101002801 → ACME 726 (599 m; 9) | 9 / 9 | 9 / 9 |
  | 3 | 42101007900 → Mariposa Food Coop (352 m; 5) | 5 / 5 | 5 / 5 |
  | 4 | 42101011700 → Shoprite of Parkside 419 (1,940 m; 33) | 33 / 33 | 19 / 27 |
  | 5 | 42101016001 → ALDI 54 (8,057 m; 119; farthest) | 119 / 119 | 38 / 38 |
  | 6 | 42101020000 → Save A Lot 60139 (1,055 m; 16) | 16 / 16 | 14 / 12 |
  | 7 | 42101025300 → Grocery Outlet 728 (533 m; 7) | 7 / 7 | 7 / 7 |
  | 8 | 42101028902 → Compare & Save Supermarket (336 m; 5) | 5 / 5 | 5 / 5 |
  | 9 | 42101033300 → Aldi 12 (364 m; 6) | 6 / 6 | 6 / 6 |
  | 10 | 42101036400 → PJP Marketplace (7,423 m; 114; farthest) | 114 / 114 | 55 / 55 |

  The coordinates of every point are printed by `route handcheck --night
  20260903T223607Z-m3-spike` (and are in `handcheck.json`); the planner
  file is `route handcheck --template`, typed by hand, tallied by `route
  handcheck --tally`. **Tally: pending.** The forty differences go here
  when the owner has them. Note for the tally: fourteen of the twenty pairs
  are short walks where walk+transit equals walk (R5 finds no faster
  transit trip); a planner that proposes a bus for a six-minute walk still
  answers within tolerance as long as its door-to-door time is within 10
  minutes.
- **The concordance:** ρ = 0.9935 over 28,256 pairs (the row above);
  `concordance.json` and `fallback_walk_times.parquet` under the night; the
  walkable ways as XML under `cache/concordance/` (171 MB). The engine is
  the fallback packet's seed if the verdict is ever kill.
- **Outcome code:** **not recorded.** The reader's suggestion is `pending
  (hand_check)`: every mechanical criterion passes, the concordance passes,
  the walk finite-pairs gate is the owner's reading, and the hand check is
  the owner's hour. The second night is **not launched** (it is the
  owner's word on a go). No fallback packet is authored (no kill).
- **Resource observations:** the night's walls and peaks per run are in
  the table above and in `phillysim/README.md`; `route verdict` takes
  seconds; the two hand-check runs 9.9 s and 9.0 s at 4.4 GB; the
  concordance 139 s with a **peak RSS of 5.46 GB in the CLI process**
  (OSMnx's XML parse of 838,148 nodes; the brief sized it at a few hundred
  megabytes: an estimate miss, recorded), well inside the 24 GB routine
  budget; the suite about 2 min.
- **Decisions and ADRs.** No ADR amended: the determinism band was
  measured, not replaced (a dated note in ADR-0008). Routine calls logged:
  the "farthest retailer inside 120 min" of the hand-check rule read by the
  core walk run's typical time (so the walk check of those two pairs has a
  finite project-side number; the transit check then covers a 38- and a
  55-minute trip); the stage re-uses a finished night and resumes a stopped
  one by plan, points, and input digests rather than re-routing; the stage
  registered ahead of the owner's code on the strength of the mechanical
  criteria, revertible by commit (decision 4); `osmnx` and `scipy` in the
  `routing` group per ADR-0008, so the OSMnx side of the concordance test
  skips in CI (decision 5); the concordance compares fractional fallback
  minutes with R5's integer minutes (ranks are what ρ measures) and adds
  both snap distances at walking speed; Spearman ρ is computed from
  pandas' average ranks (no scipy, so the comparison runs in CI);
  `verdict.json` is the reader's file and `night.json` stays the driver's.
- **Owner decisions (put to the owner interactively at the end of the
  session; answers recorded after the list):**
  1. *The finite-pairs gate for walk.* methodology.md's "≥95% finite
     pairs" read per core run is met by walk+transit (99.95 %) and cannot
     be met by walk over all 1,609 retailers under the 120-minute censor
     by any engine (the reach bound: 56.24 %). Options: (a) recommended:
     the gate is read on the walk+transit core run, and the walk run is
     reported against the straight-line reach bound (83.5 % of the pairs
     the bound admits are finite) with every origin reaching a retailer;
     recorded here, in the method card, and as one clarifying sentence in
     methodology.md "Validation" (a wording clarification of the baseline,
     not a new number: the owner's call whether that sentence is written);
     (b) read literally per core run: the walk run fails the gate and the
     verdict is KILLED-BY-EVIDENCE on a gate the fallback engine fails the
     same way; (c) re-scope the walk gate to the supermarket-format
     destinations within the reach bound (a baseline change with a new
     number).
  2. *The hand check.* The forty planner checks are a person's hour with
     SEPTA's planner and a general one. Options: (a) recommended: the
     packet stays in progress; the owner types the answers into
     `planner.csv`, runs `route handcheck --tally`, and a short closing
     session records the code, closes M3, launches the second night, and
     updates this handoff; (b) do the checks now, in this session; (c)
     accept the mechanical criteria plus the concordance as the verdict's
     evidence and defer the hand check to the third checkpoint (a
     deviation from the brief and from ADR-0008's gate: recorded as such).
  3. *The outcome code and the second night* (after 1 and 2): `go`
     recorded with `route verdict --record go`, the M3 heading closed, and
     the `travel_times` stage launched as the second unattended night by
     the README's procedure; or another code.
  4. *Commit and push.* The work is uncommitted. Recommended: commit the
     code, tests, and documentation now as the packet's work commit
     (`EP-15: …`), push, and let CI run (CI installs no routing group; the
     OSMnx-side tests skip there); the status commit follows the close.
  5. *`osmnx` and `scipy` in the `routing` group* (ADR-0008 as written),
     which keeps CI free of them and skips the OSMnx-side tests there, or a
     separate group CI installs so the concordance's graph tests run in CI
     (the brief's "the OSMnx side runs in CI on the committed OSM sample";
     a change to ADR-0008's group layout).
- **Owner answers (2026-09-03, interactive; every recommended option
  taken).** (1) *The walk gate:* the finite-pairs gate is read on the
  walk+transit core run and the walk run is reported against the
  straight-line reach bound; **applied:** one clarifying sentence in
  methodology.md "Validation", the method card's row, the README's M3
  paragraph, and this handoff; the verdict reader keeps the walk row as
  `owner-reading` so the number is never hidden. (2) *The hand check:*
  later, the packet stays in progress; the owner does the forty checks at
  their pace and a closing session tallies, records the code, closes M3,
  and launches the second night; **applied:** the status line and the
  README row read `[~]`. (3) *Commit and push now:* yes; **applied:** the
  work commit below, pushed, CI run recorded below. (4) *`osmnx` and
  `scipy` in the `routing` group:* yes, ADR-0008 as written; the
  OSMnx-side tests skip in CI; **applied:** nothing to change. (5) *The
  outcome code and the second night:* not asked yet, they follow the
  tally; the closing session asks.
- **Unresolved risks / questions.** The concordance's peak RSS (5.46 GB)
  sits in the CLI process, not a sampled child, and grows with the clip;
  a fallback packet would run it in a child under the sampler. The hand
  check's pairs 5 and 10 are 119- and 114-minute walks near the censor: a
  planner's walk time there will be over two hours, and the walk
  tolerance (15 % of about 120 min = 18 min) still applies. The stage's
  first run is the second night: the M5-gate carry-in compares its digests
  with this night's core digests (`100625cd…` walk, `e35b466d…` transit);
  it has not run yet. `route matrix`'s `--keep-awake` has no counterpart
  on `phillysim run`; the second night's launch must keep the machine
  awake by other means (or a `--keep-awake` on `run` is a small addition
  for the closing session).
- **No-go areas touched:** none. Nothing published (the public zone's
  digests are untouched: `publish` did not run and does not read the
  matrix); nothing from a trip planner stored (no planner was reached; the
  planner file is the owner's to type, under the gitignored data root);
  every new file under `data/` is gitignored (`runs/`, `cache/`); no
  machine identifier or absolute path in a tracked file (the diff scanned:
  none); the plan file carries no path; no system setting changed.
- **`roadmap/README.md`:** EP-15 row `[~]`; the M3 heading `[~]` with the
  evidence paragraph; closed by the closing session with the code.
- **Exact next packet:** this packet's closing session (the tally, the
  code, the M3 close, the second night), then **EP-16, the third
  checkpoint** (due now per EP-10 and milestones.md "Spikes & gates"; its
  fresh-clone re-run includes the unattended `travel_times` stage), unless
  the code is a kill, in which case the walk-only fallback packet (next
  free integer) comes first if the owner so decides.
