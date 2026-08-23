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
  in a demonstrable increment with a go/no-go criterion.
- Near-horizon work is decomposed into issue-ready **work packets (EP-N)** in
  [packets.md](packets.md), sized for one bounded coding-agent session each.
  Later milestones stay at outcome level until their **refinement gate**.
- Estimates use **agent sessions** (one focused, tested, committed sitting)
  with S/M/L labels: S ≈ ≤1 session, M ≈ 1–2, L ≈ must be split.
- Architecture-level or hard-to-reverse choices are recorded in [adr/](adr/).
- Status convention: `[ ]` planned · `[~]` in progress · `[x] <commit>` done.

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
| [milestones.md](milestones.md) | Milestones, dependencies, critical path, risks, effort roll-up |
| [packets.md](packets.md) | Issue-ready near-horizon work packets (EP-01 …) |
| [_TEMPLATE.md](_TEMPLATE.md) | Work-packet template with safety preconditions |

## Phase overview

| Phase | Milestones | Outcome | Status |
|---|---|---|---|
| Foundation | M0–M1 | Governed repo + pipeline skeleton proven on synthetic fixture | [ ] |
| First data | M2 | Real geography + first source end-to-end, reproducibly | [ ] |
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
