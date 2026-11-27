# phillysim roadmap

**phillysim** measures and maps access to health-relevant community resources
across Philadelphia at the census-tract level, built to a scientific-evidence
standard. v1 is descriptive access *measurement* — not simulation, prediction,
or clinical decision support. See [charter.md](charter.md) for what this
project is and is not, and for what "sim" in the name does and does not mean.

This roadmap implements **Planning Baseline v1.0** (approved 2026-08-23),
produced through a gated discovery-and-research process: a 15-domain discovery
interview, five specialist research workstreams with first-party evidence, and
an adversarial red-team review whose findings (1 blocker, 7 material, 9 minor)
were all resolved before this roadmap was drafted.

From 2026-11-11 its phase tables follow the house style shared by every
project under `DATA` ([DECISIONS.md](../DECISIONS.md) D-1): the header
`| # | Brief | Size | Depends on | Core | Done |`, a done row's cell `☑` with
its commit hash, an open row's `☐`, and the next brief the first unchecked
row in table order. The packet vocabulary, the briefs and their handoff
payloads are as they were.

**Sweep (2026-11-25, inbox IN-1).** Settled with the owner in Roadmap
Wrangler's sweep of its projects that were not active: the project is
**active** (the state on its row in Roadmap Wrangler is the owner's to
set), with EP-16 the next work. It is **formalised**: `CLAUDE.md` holds the
session rules, the project's own above Roadmap Wrangler's block, and
`roadmap/owner-tasks.md` sits beside `roadmap/inbox.md`; new briefs keep the
work-packet template, now with YAML front matter and a closing completion
note ([DECISIONS.md](../DECISIONS.md) D-3). A brief is **S (about 30
minutes of active work) or M (about 45)**, never L, and a row that proves
larger at pickup is split there (D-2, "Packet sizing and splitting" below),
EP-16 first. It owes **no manual yet**: there is no `docs/manual.md`, so no
brief writes a changes section; the question comes back at the M6 gate (the
public site) or on the owner's word. How far v1 runs is stated under the
M4–M8 heading (inbox IN-2). The house-style migration of 2026-11-11 was
committed first, as `6dcf11d`.

## How to read this roadmap

- Milestones **M0–M8** are listed in [milestones.md](milestones.md). Each ends
  in a demonstrable increment with a go/no-go criterion. The
  [milestone ↔ packet tables](#milestones-and-work-packets) below are where
  packet and milestone status is tracked; each packet file's header carries
  the same status.
- Near-horizon work is decomposed into issue-ready **work packets**, one file
  per packet (`EP-N-<slug>.md`, from [_TEMPLATE.md](_TEMPLATE.md)), each
  sized for **one** bounded coding-agent session. EP-1–EP-8 cover M0–M2; later
  milestones stay at outcome level until their **refinement gate**, where new
  EP files are authored (the M3 gate is [EP-11](EP-11-m3-refinement-gate.md),
  which authored EP-12–EP-15 on 2026-09-03). **At a refinement gate, first apply that
  milestone's entries under "Refinement-gate carry-ins" in
  [milestones.md](milestones.md)** — they are deferred obligations from
  earlier packets, with the text to paste into the new EP files.
- Estimates use **agent sessions** (one focused, tested, committed sitting).
  One packet is one session; see "Packet sizing and splitting" below.
  *(2026-11-25, D-2: a packet is now S, about 30 minutes of active work, or
  M, about 45; the estimates written before then count the older sittings.)*
- Architecture-level or hard-to-reverse choices are recorded in [adr/](adr/).
- Status convention (house style, 2026-11-11, D-1): a row's Done cell is `☐`
  until its brief is committed, then `☑` and one backticked commit hash
  (the commit that landed the work; the handoff commit follows it); a
  milestone heading carries the same mark once its go/no-go holds. The
  next brief is the first unchecked row in table order. A brief's own
  header line keeps the older `[x] <commit>` form; a brief written from
  the template as amended on 2026-11-25 (D-3) carries its status in its
  YAML front matter instead (`planned`, `in progress`, `done`) and ends
  with a completion note.

### Packet sizing and splitting

*(2026-11-25, D-2, the owner's sweep.)* From this date a packet is **S**
(about 30 minutes of active work) or **M** (about 45), as the Sizes bullet
in `CLAUDE.md` says: an S where its shape is known when it is written and
it touches a handful of files, an M for an investigation, a state machine
or the choice of a tool. **L** stays invalid. A packet is not cut only to
make it smaller, and one that proves larger at pickup is split there by the
convention below, never run long; EP-16, written as "S (1 session)", is the
first (split at its pickup on 2026-11-26 into six M parts, EP-16a to
EP-16f). The bullets below are the rule as it stood from 2026-09-02, under
which every row up to EP-16 was sized; their Size cells stay as written.

- **S** — fits one session. Every packet authored from 2026-09-02 on is S:
  refinement gates decompose a milestone's outcome into S packets rather
  than authoring anything larger.
- **M** (1–2 sessions) survives only in the M2 packets written before this
  rule (EP-5–EP-8). At pickup, the session reads the packet and decides
  whether it fits one session; if not, it is **split before any work
  starts**, using the convention below. EP-5 was split into EP-5a / EP-5b
  by the EP-9 pre-read on 2026-09-02; EP-6 and EP-7 were each read at
  pickup the same day, judged to fit one session, and did; EP-8 was read at
  pickup the same day and split into EP-8a / EP-8b (the page versus a new
  roads source for the basemap); each half fit one session. No M packet
  remains.
- **L** is no longer a valid packet size. The one L packet, EP-4, was split
  on 2026-09-02 into EP-4a and EP-4b at the engine/runner boundary its own
  brief allowed.
- **Split convention.** An already-numbered packet that must be split keeps
  its number and gains letter suffixes — `EP-Na-<slug>.md`, `EP-Nb-<slug>.md`,
  … — each a complete packet from the template with `Split from: EP-N` in
  its header line, sequenced a → b → …, the last part carrying the parent's
  milestone-level acceptance evidence. The bare `EP-N` then names the set,
  never a packet of its own, so existing references to it (CHANGELOG, other
  packets, handoffs) stay valid. Suffixes are a pickup remedy only: new
  packets are never authored with them, and the next new packet takes the
  next free integer.

## Document index

| Doc | Contents |
|---|---|
| [charter.md](charter.md) | Charter, users, intended/prohibited uses, claims, success evidence, non-goals, publication plan |
| [scope.md](scope.md) | v1 / v1.x / v2 scope, MoSCoW priorities, promotion/kill gates, vertical slice |
| [sources.md](sources.md) | Source-feasibility and licensing matrix, fallbacks, refresh strategy |
| [methodology.md](methodology.md) | Constructs, algorithms, parameters, uncertainty, sensitivity, validation, fairness |
| [architecture.md](architecture.md) | Components, pipeline, stack rationale, budgets, upgrade triggers |
| [governance.md](governance.md) | Privacy, security, community safety, clinical boundaries, accessibility, maintenance |
| [quality.md](quality.md) | Versioning axes, test matrix, release gates, reproducibility procedure |
| [milestones.md](milestones.md) | Milestones, dependencies, critical path, risks, effort roll-up, refinement-gate carry-ins |
| [open-questions.md](open-questions.md) | Open questions and consciously deferred items (OQ-A …) |
| [EP-1](EP-1-governance-bootstrap.md) … [EP-8](EP-8-slice-page.md) | Issue-ready work packets, one file each (M0–M2; EP-4 split into [EP-4a](EP-4a-manifest-engine.md) / [EP-4b](EP-4b-stage-runner.md); EP-5 split into [EP-5a](EP-5a-spine-acquisition.md) / [EP-5b](EP-5b-spine-curated.md); EP-8 split into [EP-8a](EP-8a-slice-page.md) / [EP-8b](EP-8b-basemap-roads.md)); later EPs authored at refinement gates |
| [EP-9](EP-9-checkpoint-1.md), [EP-10](EP-10-checkpoint-2.md), [EP-16](EP-16-checkpoint-3.md) | Checkpoint packets: the first after M1 (before EP-5), the second after M2 (before the M3 refinement gate, which EP-10 authored as EP-11), the third after M3 (authored by EP-15's closing session; split at pickup on 2026-11-26 into [EP-16a](EP-16a-dependency-triage.md) … [EP-16f](EP-16f-m4-gate-preread.md), the last of which pre-reads the M4 gate and authors it as EP-17); later checkpoints take the next free integer |
| [EP-11](EP-11-m3-refinement-gate.md) | The M3 refinement gate: a documentation-only packet that decomposes the routing spike into S packets, EP-12 onward; its pins and decision numbers are [ADR-0008](adr/0008-routing-toolchain-pins.md) |
| [EP-12](EP-12-routing-sources.md) … [EP-15](EP-15-routing-verdict.md) | The M3 routing spike as authored by EP-11 (2026-09-03): the two routing sources ([EP-12](EP-12-routing-sources.md)), the toolchain and harness ([EP-13](EP-13-routing-toolchain-harness.md)), the run matrix and the first unattended night ([EP-14](EP-14-routing-run-matrix.md)), the verdict ([EP-15](EP-15-routing-verdict.md)); a walk-only fallback packet is authored by EP-15 only on a kill |
| [_TEMPLATE.md](_TEMPLATE.md) | Work-packet template with safety preconditions; YAML front matter, the sizes of D-2 and a closing completion note since 2026-11-25 (D-3) |
| [owner-tasks.md](owner-tasks.md) | What only the owner can do, one line each (house style, since 2026-11-25) |
| [inbox.md](inbox.md) | Messages from other projects and from the owner through Roadmap Wrangler, triaged at a session's start |

## Milestones and work packets

One row per packet, grouped by milestone. A milestone is done when every
packet in its table is done and its go/no-go criterion in
[milestones.md](milestones.md) holds; the milestone heading records that
with the same status convention. A packet's session ends by updating its row
here (its Done cell: `☑` and the commit) as part of the handoff. Milestones M3–M8 get tables
at their refinement gates.

### M0 — Governance bootstrap · ☑ `9bcb7b2`

Go/no-go: all M0 packets' acceptance criteria met; repo presentable at any
commit. Met 2026-09-02 with EP-2.

| # | Brief | Size | Depends on | Core | Done |
|---|---|---|---|---|---|
| EP-1 | [Repository governance bootstrap](EP-1-governance-bootstrap.md) | S | — | core | ☑ `102af00` |
| EP-2 | [Python scaffold + offline CI skeleton](EP-2-scaffold-ci.md) | M | EP-1 | core | ☑ `9bcb7b2` |

### M1 — Pipeline skeleton + fixture · ☑ `9a0a3dc`

Go/no-go: `phillysim run --fixture` green in offline CI. Met 2026-09-02 with
EP-4b: CI runs `phillysim run --fixture`, `status --fixture`, and
`verify --fixture` on Windows and Linux, and the integration suite asserts
the curated outputs equal the golden tables.

| # | Brief | Size | Depends on | Core | Done |
|---|---|---|---|---|---|
| EP-3 | [tinycity synthetic fixture](EP-3-tinycity-fixture.md) | M | EP-2 | core | ☑ `4ed065a` |
| EP-4a | [Manifest/snapshot engine + zones + download guards](EP-4a-manifest-engine.md) | S | EP-3 | core | ☑ `361b1eb` |
| EP-4b | [Stage runner: fingerprints, resume/cancel, preflight, `run/status/verify`](EP-4b-stage-runner.md) | S | EP-4a | core | ☑ `9a0a3dc` |

### Checkpoints · recurring

Recurring S-sized checkpoint packets ([milestones.md](milestones.md)
"Spikes & gates": every ~5 packets): integration re-run on fixtures (plus
the real spine once it exists), docs/data-dictionary sync, license-label
sweep, performance vs budgets, estimate-accuracy review, re-plan if a
trigger fires. They belong to no milestone; the packet that follows one
depends on it. The first fell due with EP-4b (owner decision 2026-09-02)
and closed on 2026-09-02; the second fell due with EP-8b (M2 done) and was
authored on 2026-09-03 as EP-10 and closed the same day, authoring the M3
refinement gate as its own documentation-only packet, EP-11 (owner
decision 2026-09-03); the third fell due with EP-15 (M3 closed on
2026-09-04) and was authored by EP-15's closing session as EP-16, the next
packet, whose fresh-clone re-run includes the unattended `travel_times`
stage; its pickup on 2026-11-26 split it under D-2 into six M parts, EP-16a
to EP-16f, the dependency triage first; the fourth falls due about five
packets after EP-16 (EP-16e re-reads that cadence under D-2).

| # | Brief | Size | Depends on | Core | Done |
|---|---|---|---|---|---|
| EP-9 | [Checkpoint 1: fixture re-run, docs sync, license sweep, budgets, estimate accuracy](EP-9-checkpoint-1.md) | S | EP-4b | core | ☑ `84c9ec1` |
| EP-10 | [Checkpoint 2: fresh-clone re-run with real data, docs sync, license sweep on published output, budgets, dependency triage, estimate accuracy, M3 gate pre-read](EP-10-checkpoint-2.md) | S | EP-8b | core | ☑ `a1d22fd` |
| EP-16a | [Dependency triage with the owner (certifi first), the lock checked, the pins noted](EP-16a-dependency-triage.md) | M | EP-15 (M3 done) | core | ☑ `0597ab5` |
| EP-16b | [Fresh-clone re-run, fixture and real, with the routing night; resource use against the budgets, peak RSS included](EP-16b-fresh-clone-rerun.md) | M | EP-16a | core | ☐ |
| EP-16c | [License-label sweep on the real published output and the Bucket B zone; the dictionary, data cards and license records checked](EP-16c-license-sweep-data-docs.md) | M | EP-16b | core | ☐ |
| EP-16d | [Documentation sync of the READMEs, method cards, claims, roadmap documents, ADR-0008 and the changelog against the code](EP-16d-docs-sync.md) | M | EP-16c | core | ☐ |
| EP-16e | [Estimate-accuracy review with the M3 actual, the re-plan triggers, and v1 counted in briefs under D-2](EP-16e-estimate-review.md) | M | EP-16d | core | ☐ |
| EP-16f | [M4 refinement-gate pre-read, EP-17 authored, and the checkpoint's acceptance evidence](EP-16f-m4-gate-preread.md) | M | EP-16e | core | ☐ |

**Brief notes.**

**The EP-16 set (split 2026-11-26).** Checkpoint 3 was authored on
2026-09-04 by EP-15's closing session as one packet, "S (1 session)", with
seven scope items ([EP-16-checkpoint-3.md](EP-16-checkpoint-3.md), now the
set's name). Its pickup on 2026-11-26 split it before any work started, as
the brief note from IN-1 asked and D-2 requires, into six M parts along its
own items: the dependency triage first (the owner's choice at the sweep's
push, so that the re-run tests the lock the triage leaves), then the
fresh-clone re-run with the resource use it measures, the license sweep with
the data-facing documents, the rest of the documentation sync, the estimate
review, and the M4 pre-read with EP-17, the last carrying the set's
acceptance evidence. The note's segments moved to the parts they concern:
the sweep's push (42 alerts, 11 pull requests, certifi critical) into EP-16a's
brief, the rest to the bullets below.

- **EP-16b.** The fresh clone reads the pushed `main`: the split and
  EP-16a's lock reach it only once the owner pushes them (OT-1, gated before
  this brief). Whether the seven providers still serve the pinned files is
  unchecked since the last fresh acquisitions (EP-10 and EP-12, 2026-09-03);
  a failed or changed fetch is the brief's own stop and owner decision.
  `phillysim run` has no `--keep-awake`, so the machine is kept awake by
  hand for the night. **From EP-16a (2026-11-26):** after the push, check
  that Dependabot has closed the six pull requests EP-16a's lock and CI pin
  supersede (#10 to #15) and that the 35 alerts on `phillysim/uv.lock` read
  fixed; any left open is put to the owner. The three runtime version
  updates (#6 to #8) stay out of the clone's lock by the owner's decision.
- **EP-16c.** It sweeps the working clone's installed real public zone,
  which EP-16b shows byte-equal to the fresh clone's (the scratch clone is
  deleted by then), and the working clone's two nights for the Bucket B
  records.
- **EP-16d.** EP-16a's upgrades and EP-16b's baselines are in view when the
  CHANGELOG and the READMEs are checked.
- **EP-16e.** **From IN-2 (2026-11-25):** the estimate review also restates
  the remaining v1 work, M4 to M7 with their gates and checkpoints, as a
  count of briefs under D-2, from milestones.md's high bounds and the M3
  actual, and settles with the owner which rows carry it in the tables
  (gate rows, provisional rows or none), so that the count Roadmap
  Wrangler's site export reads says how far v1 runs ("How far v1 runs"
  under the M4–M8 heading); it also re-reads the checkpoint cadence ("every
  ~5 packets"), set under the old sizes. **From IN-3 (2026-11-26, the owner
  through prime):** the portfolio card's floor is now 57 (the 19 rows then;
  M4 7, M5 7, M6 10 and M7 4 sessions, 28; 4 refinement gates and about 6
  checkpoints), so the card reads 18 of about 57; when the rows cover v1,
  hand on to prime so that its IN-5 drops the floor, and a count under 57
  is said at once. At the split the tables went to 24 rows, 62 by the same
  sum, and restating the older sessions as S or M briefs only raises it, so
  nothing was said at once (EP-16a).
- **EP-16f.** It opens the "M4 — Full ingest" heading with EP-17's row,
  trims the M5 carry-in's first item once EP-16b has confirmed the
  cross-clone repeat, and completes EP-16's row in "Estimate accuracy".
  **From EP-16a (2026-11-26):** it carries the three runtime version updates
  the owner deferred (Dependabot #6 geopandas 1.1.4 → 1.2.0, #7 pyproj
  3.7.2 → 3.8.0, #8 duckdb 1.5.5 → 1.5.6, duckdb 2.0.1 also out) into
  EP-17's inputs: a deliberate upgrade after EP-16b has confirmed the
  reference digests, with the references re-recorded (these libraries
  compute the ingest and conflation M4 adds).

### M2 — Spine + first source end-to-end · ☑ `5cb5092`

Go/no-go: slice reproducible from a fresh clone; license buckets applied.
Met 2026-09-03 with EP-8b: the eight-stage real pipeline reproduces the
public zone byte for byte from a fresh clone (digests in the EP-7 and EP-8b
handoffs), every public file carries the bucket derived from its sources
and passes the gate (Bucket A / CC BY 4.0 on the real slice, Bucket B on
the fixture, both gated in CI), and the minimal page renders the zone over
the ADR-0005 basemap (county boundary plus TIGER major roads) with axe and
the browser tests green on both platforms.
Each M-sized packet is read at pickup and split (convention above) if it
will not fit one session. EP-9 did that pre-read for EP-5 on 2026-09-02 and
split it into EP-5a / EP-5b; the EP-8 pickup did the same on 2026-09-02 and
split it into EP-8a / EP-8b. [EP-5](EP-5-spine-adapters.md) and
[EP-8](EP-8-slice-page.md) now name their sets.

| # | Brief | Size | Depends on | Core | Done |
|---|---|---|---|---|---|
| EP-5a | [Spine source adapters: acquisition path + TIGER/CenPop/ACS snapshots](EP-5a-spine-acquisition.md) | S | EP-9 (checkpoint), EP-4b | core | ☑ `39a6828` |
| EP-5b | [Curated tract spine + geospatial invariants + analysis-CRS ADR](EP-5b-spine-curated.md) | S | EP-5a | core | ☑ `b61d060` |
| EP-6 | [SNAP retailer adapter + supermarket-format classification](EP-6-snap-adapter.md) | M | EP-5 (= EP-5b) | core | ☑ `907f8f8` |
| EP-7 | [Thin-slice metric + public zone + license bucketing](EP-7-slice-publish.md) | M | EP-6 | core | ☑ `bf9df7f` |
| EP-8a | [Minimal slice page: map + table from the public zone, county-boundary basemap, Playwright + axe](EP-8a-slice-page.md) | S | EP-7 | core | ☑ `dd66884` |
| EP-8b | [Basemap roads: TIGER major-roads source, roads layer, contrast check; M2 closes](EP-8b-basemap-roads.md) | S | EP-8a | core | ☑ `5cb5092` |

### M3 — Routing spike · ☑ `9638bd2`

Go/no-go: numeric criteria in [milestones.md](milestones.md) (wall ≤ 8 h,
process-tree RSS ≤ 22 GB, determinism within band, sanity gates); go =
walk+transit within budgets, kill = the documented walk-only fallback
invoked. **Evidence (EP-15, 2026-09-03 and 2026-09-04, on the first unattended night
`20260903T223607Z-m3-spike`, read by `phillysim route verdict`):** the two
core runs together took 830 s of the 8 h wall (walk 54 s, walk+transit
776 s; all seven runs of the matrix in 47 min); the peak process-tree RSS
over the night was 5.39 GB against the 20 GB budget and the 22 GB kill
line, no run killed; both core runs were identical to their repeats pair
for pair (656,472 of 656,472 pairs each, both time columns, byte and
canonicalized-value digests equal), so OQ-C closes with a measured band of
zero; the walk+transit core run has 99.95 % finite pairs against the 95 %
gate, and the walk core run 46.95 % under the 120-minute censor, where the
straight-line reach bound at 4.8 km/h admits at most 56.24 % of the pairs
(every origin reaches a retailer; owner decision at EP-15: the gate is read
on the walk+transit run and the walk run is reported against the reach
bound, recorded in methodology.md "Validation"); the walk concordance
against the fallback engine (OSMnx 2.1.1 + scipy on the same clip) is
Spearman ρ = 0.9935 over 28,256 pairs both engines report under the
censor, against the 0.95 gate; the hand check (ten pairs by rule, 08:30
and 17:30, walk and walk+transit, compared by hand against SEPTA's planner
and a general planner) tallied **34 of 40** within tolerance against the
32-of-40 gate (walk 14 of 20, walk+transit 20 of 20; the six misses are
walk checks 5 to 8 minutes under the planner on short trips, a finding
for the M5 method card). **Outcome code: go**, confirmed by the owner on
2026-09-04 and recorded in the night's `verdict.json`. The `travel_times`
stage (EP-15) ran its first night the same day as the second unattended
night (`20260904T191646Z-travel-times`: the two core runs in 886 s of child wall,
peak RSS 5.26 GB, both matrices' canonicalized-value digests
equal to the spike's night), so `curated/travel_times.parquet` exists in
the dictionary's shape, Bucket B and unpublished, and the third
checkpoint, [EP-16](EP-16-checkpoint-3.md), is due next. A gate packet belongs to the milestone it refines (unlike a
checkpoint, which belongs to none): EP-11 is the M3 refinement gate,
authored by EP-10 on 2026-09-03 from its pre-read. It applied the
`milestones.md` carry-ins first (none named M3), fixed the spike's inputs,
sources, pins, and decision numbers in
[ADR-0008](adr/0008-routing-toolchain-pins.md) with the owner, and authored
the four packets below from [_TEMPLATE.md](_TEMPLATE.md) as S packets, one
session each: the sources first (adapter work without a JVM), the toolchain
and harness next (whose smoke route needs the clipped network), then the
pre-scripted run matrix launched as an unattended night, then the verdict.
The attended spike box of milestones.md (three sessions) is EP-13 to EP-15;
unattended nights are outside it; one owner-approved extension is one
further attended packet and one more night. EP-15 closes this heading
with the go/no-go evidence and authors the walk-only fallback packet only
on a kill or an exhausted time box.

| # | Brief | Size | Depends on | Core | Done |
|---|---|---|---|---|---|
| EP-11 | [M3 refinement gate: decompose the routing spike into S packets](EP-11-m3-refinement-gate.md) | S | EP-10 (checkpoint) | core | ☑ `c6b5372` |
| EP-12 | [Routing sources: OSM extract (Geofabrik, Bucket B) and SEPTA GTFS through the guarded path; per-source snapshot IDs; the clipped network](EP-12-routing-sources.md) | S | EP-11 | core | ☑ `a4c8a38` |
| EP-13 | [Routing toolchain and harness: pinned JDK 21 and R5 jar, r5py behind the wheel-only rule, the RSS sampler, run records, the smoke route, CI performance smoke](EP-13-routing-toolchain-harness.md) | S | EP-12 | core | ☑ `e4c2c95` |
| EP-14 | [The pre-scripted run matrix and the first unattended night](EP-14-routing-run-matrix.md) | S | EP-13 | core | ☑ `b35370d` |
| EP-15 | [The M3 verdict: criteria against the records, the determinism band, the hand check, go or kill; M3 closes](EP-15-routing-verdict.md) | S | EP-14 (its night finished) | core | ☑ `9638bd2` |

### M4–M8 · ☐ refinement gates pending

No packet files exist yet. The M4 (full ingest) gate and later gates follow
the procedure EP-11 established for M3 on 2026-09-03: a documentation-only
S packet per milestone that applies that milestone's carry-ins first,
reads the documents its pre-read lists, puts every hard-to-reverse value in
an ADR with the owner (as ADR-0008 does for M3), and authors its packets
from [_TEMPLATE.md](_TEMPLATE.md) as S packets, one session each, taking
the next free integers and adding their rows here. The M4 gate is the
next gate due (M4 parallels M3 and depends on M2 only); the third
checkpoint, [EP-16](EP-16-checkpoint-3.md), pre-reads it and authors it as
EP-17 (its last part, [EP-16f](EP-16f-m4-gate-preread.md)).

*(2026-11-25, inbox IN-2.)* **How far v1 runs.** v1 is M0 to M7, the
v1.0.0 release; M8, the v1.x/v2 gate decisions, follows it. By
[milestones.md](milestones.md), planned at its high bounds (owner decision
2026-09-03), the v1 milestones still ahead are M4 at 7 sessions, M5 at 7,
M6 at 10 and M7 at 4, as sized before D-2, each opened by its refinement
gate (which now authors S or M packets, D-2), with a checkpoint about every
five packets, EP-16 the next. None of them has rows yet, so the tables'
count, which Roadmap Wrangler's site export reads, covers the work planned
so far, not v1. EP-16's estimate review ([EP-16e](EP-16e-estimate-review.md))
restates the remaining v1 work as a count of briefs under D-2 and settles
with the owner which rows carry it.

## Phase overview

| Phase | Milestones | Outcome | Status |
|---|---|---|---|
| Foundation | M0–M1 | Governed repo + pipeline skeleton proven on synthetic fixture | [x] M0 and M1 done |
| First data | M2 | Real geography + first source end-to-end, reproducibly | [x] M2 done |
| Routing | M3 | Travel-time spike passed or walk-only fallback invoked | [x] M3 done (verdict go, 2026-09-04) |
| Full ingest | M4 | All v1 sources snapshotted, conflated, hours-parsed | [ ] |
| Metrics | M5 | Access metrics + uncertainty + validation vs SRAM | [ ] |
| Site | M6 | Public-safe accessible map + table + methods pages | [ ] |
| Release | M7 | Reviews passed, v1.0.0 reproducible release | [ ] |
| Beyond | M8 | Evidence-based v1.x/v2 gate decisions | [ ] |

## Provenance and AI disclosure

This project is developed with AI coding agents under human direction and
review; the author is accountable for all published content. Roadmap and
research artifacts were likewise AI-assisted and human-approved. This roadmap
does not imply endorsement by the City of Philadelphia, any data provider,
employer, or community organization.
