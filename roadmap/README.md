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
  EP files are authored. **At a refinement gate, first apply that
  milestone's entries under "Refinement-gate carry-ins" in
  [milestones.md](milestones.md)** — they are deferred obligations from
  earlier packets, with the text to paste into the new EP files.
- Estimates use **agent sessions** (one focused, tested, committed sitting).
  One packet is one session; see "Packet sizing and splitting" below.
- Architecture-level or hard-to-reverse choices are recorded in [adr/](adr/).
- Status convention: `[ ]` planned · `[~]` in progress · `[x] <commit>` done
  (the commit that landed the work; the handoff commit follows it).

### Packet sizing and splitting

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
| [EP-9](EP-9-checkpoint-1.md) | First checkpoint packet (after M1, before EP-5); later checkpoints take the next free integer |
| [_TEMPLATE.md](_TEMPLATE.md) | Work-packet template with safety preconditions |

## Milestones and work packets

One row per packet, grouped by milestone. A milestone is done when every
packet in its table is done and its go/no-go criterion in
[milestones.md](milestones.md) holds; the milestone heading records that
with the same status convention. A packet's session ends by updating its row
here (status + commit) as part of the handoff. Milestones M3–M8 get tables
at their refinement gates.

### M0 — Governance bootstrap · `[x] 9bcb7b2`

Go/no-go: all M0 packets' acceptance criteria met; repo presentable at any
commit. Met 2026-09-02 with EP-2.

| # | Packet | Size | Depends on | Status |
|---|---|---|---|---|
| EP-1 | [Repository governance bootstrap](EP-1-governance-bootstrap.md) | S | — | [x] 102af00 |
| EP-2 | [Python scaffold + offline CI skeleton](EP-2-scaffold-ci.md) | M | EP-1 | [x] 9bcb7b2 |

### M1 — Pipeline skeleton + fixture · `[x] 9a0a3dc`

Go/no-go: `phillysim run --fixture` green in offline CI. Met 2026-09-02 with
EP-4b: CI runs `phillysim run --fixture`, `status --fixture`, and
`verify --fixture` on Windows and Linux, and the integration suite asserts
the curated outputs equal the golden tables.

| # | Packet | Size | Depends on | Status |
|---|---|---|---|---|
| EP-3 | [tinycity synthetic fixture](EP-3-tinycity-fixture.md) | M | EP-2 | [x] 4ed065a |
| EP-4a | [Manifest/snapshot engine + zones + download guards](EP-4a-manifest-engine.md) | S | EP-3 | [x] 361b1eb |
| EP-4b | [Stage runner: fingerprints, resume/cancel, preflight, `run/status/verify`](EP-4b-stage-runner.md) | S | EP-4a | [x] 9a0a3dc |

### Checkpoints · recurring

Recurring S-sized checkpoint packets ([milestones.md](milestones.md)
"Spikes & gates": every ~5 packets): integration re-run on fixtures (plus
the real spine once it exists), docs/data-dictionary sync, license-label
sweep, performance vs budgets, estimate-accuracy review, re-plan if a
trigger fires. They belong to no milestone; the packet that follows one
depends on it. The first fell due with EP-4b (owner decision 2026-09-02)
and closed on 2026-09-02; the next falls due after about five more packets
(EP-5a, EP-5b, EP-6, EP-7, EP-8), that is, after EP-8 and before the M3
refinement gate, and takes the next free integer.

| # | Packet | Size | Depends on | Status |
|---|---|---|---|---|
| EP-9 | [Checkpoint 1: fixture re-run, docs sync, license sweep, budgets, estimate accuracy](EP-9-checkpoint-1.md) | S | EP-4b | [x] 84c9ec1 |

### M2 — Spine + first source end-to-end · `[x] EP8B_COMMIT`

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

| # | Packet | Size | Depends on | Status |
|---|---|---|---|---|
| EP-5a | [Spine source adapters: acquisition path + TIGER/CenPop/ACS snapshots](EP-5a-spine-acquisition.md) | S | EP-9 (checkpoint), EP-4b | [x] 39a6828 |
| EP-5b | [Curated tract spine + geospatial invariants + analysis-CRS ADR](EP-5b-spine-curated.md) | S | EP-5a | [x] b61d060 |
| EP-6 | [SNAP retailer adapter + supermarket-format classification](EP-6-snap-adapter.md) | M | EP-5 (= EP-5b) | [x] 907f8f8 |
| EP-7 | [Thin-slice metric + public zone + license bucketing](EP-7-slice-publish.md) | M | EP-6 | [x] bf9df7f |
| EP-8a | [Minimal slice page: map + table from the public zone, county-boundary basemap, Playwright + axe](EP-8a-slice-page.md) | S | EP-7 | [x] dd66884 |
| EP-8b | [Basemap roads: TIGER major-roads source, roads layer, contrast check; M2 closes](EP-8b-basemap-roads.md) | S | EP-8a | [~] |

### M3–M8 · `[ ]` refinement gates pending

No packet files exist yet. With M2 done, the second checkpoint comes first
(the next free integer, EP-10; see "Checkpoints" above), then the M3
(routing spike) and M4 (full ingest) refinement gates author their packets
from [_TEMPLATE.md](_TEMPLATE.md) — carry-ins first — as S packets, one
session each, numbered from the next free integer after it. Later gates
follow the same procedure.

## Phase overview

| Phase | Milestones | Outcome | Status |
|---|---|---|---|
| Foundation | M0–M1 | Governed repo + pipeline skeleton proven on synthetic fixture | [x] M0 and M1 done |
| First data | M2 | Real geography + first source end-to-end, reproducibly | [x] M2 done |
| Routing | M3 | Travel-time spike passed or walk-only fallback invoked | [ ] |
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
