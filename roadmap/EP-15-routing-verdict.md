# EP-15 — The M3 verdict: criteria against the records, the determinism band, the hand check, go or kill, M3 closes

**Status:** [ ] planned · **Milestone:** M3 · **Effort:** S (1 session, medium confidence) · **Parallel with:** —

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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- the verdict table; the determinism numbers; the hand-check tally and
  the forty differences; the concordance ρ and the pair counts; the
  outcome code and the owner's confirmation; on go the second night's
  launch; on kill the fallback packet's ID
- resource observations (the night's wall per run; the peak RSS)
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none; nothing published; nothing from the
  planner stored)
- `roadmap/README.md` packet row updated to `[x] <commit>` and the M3
  heading closed
- exact next packet: the third checkpoint (next free integer; due with
  this packet per EP-10), or on kill the fallback packet first if the
  owner so decides
