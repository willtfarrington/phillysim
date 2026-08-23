# phillysim

**Measuring access to health-relevant community resources across Philadelphia**
— at the 2020 census-tract level, presented as an accessible public map, table,
and narrative. A local-first, public-interest civic-data project.

This project **measures access; it does not model outcomes**. v1 is descriptive
access measurement: no simulation, no prediction, no clinical decision support,
no scores or rankings.

## On the name

"sim" is aspirational lineage with the author's sibling projects, not a claim.
v1 contains no simulation. A scenario layer (e.g., "what changes if a site
closes?") may only be added if a future evidence gate is passed; until then the
project describes — it does not simulate, predict, or prescribe. See
[roadmap/charter.md](roadmap/charter.md).

## What v1 will do

- Measure access — travel time on foot and by walk+transit — from every 2020
  census tract in Philadelphia County to food resources relevant to people
  managing diet-sensitive chronic conditions: SNAP-authorized
  supermarket-format stores, farmers' markets, and free food & meal sites.
- Publish transparent, component-level metrics with uncertainty
  (margin-of-error propagation and reliability flags) displayed beside every
  result. No composite indices, no ranked lists.
- Ship as a static, accessible site (WCAG 2.2 AA target) with a full-parity
  table and narrative view, backed by a reproducible, manifest-checked local
  pipeline.

The intended primary use is *aggregate, locality-aware* planning — for
example, preparing discharge-education materials and social-work briefings
that reflect the real resource landscape patients return to. Area-level
measures are never presented as individual risk, and the project publishes no
patient-specific tools or advice.

## What this project deliberately is not

No clinical decision support, patient flagging, or EHR integration. No hosted
backend. No address-entry or geolocation features. No predictive, causal, or
outcome claims. No "food desert" labels, food-insecurity measurement, or
diet-quality evaluation — the project measures **access**, which is not the
same as affordability, inventory, or suitability. The full claims discipline
lives in [docs/CLAIMS.md](docs/CLAIMS.md) and
[roadmap/charter.md](roadmap/charter.md).

## Status

Early stage. The project is governed before it is built: the accepted planning
baseline and work packets live in [roadmap/](roadmap/), and this repository
currently contains governance documents, not pipeline code. Progress is
tracked in [CHANGELOG.md](CHANGELOG.md) and the packet files
(`roadmap/EP-*.md`).

## Documents

| Document | Contents |
|---|---|
| [roadmap/](roadmap/) | Charter, scope, sources, methodology, architecture, governance, quality, milestones, work packets, ADRs |
| [docs/CLAIMS.md](docs/CLAIMS.md) | Claims matrix: what the project may and may not say, mapped to evidence |
| [docs/DATA-LICENSES.md](docs/DATA-LICENSES.md) | Per-source data licensing, the City-license caveat, and output license buckets |
| [docs/policies.md](docs/policies.md) | Correction/feedback channel and delisting/takedown policy |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to report issues and propose changes |
| [SECURITY.md](SECURITY.md) | How to report security issues |

## Provenance and AI disclosure

This project is developed with AI coding agents under human direction and
review; the author is accountable for all published content. Planning and
research artifacts were likewise AI-assisted and human-approved.

## Non-endorsement

This is an independent personal project. It does not imply endorsement by, or
affiliation with, the City of Philadelphia, any data provider, any employer,
or any community organization. Data sources are credited in
[docs/DATA-LICENSES.md](docs/DATA-LICENSES.md); their originators' terms
govern their use.

## Source material

`source material/opendataphilly-jkan-main/` is an unmodified copy of
[opendataphilly/opendataphilly-jkan](https://github.com/opendataphilly/opendataphilly-jkan),
included here for reference only. That code, its dataset records, and its
assets are the work of the OpenDataPhilly contributors and are used under the
MIT License; the upstream `LICENSE` file is retained in that directory. No part
of it is authored by this project.

## License

Original code and text in this repository are MIT licensed — see
[LICENSE](LICENSE). Published data outputs will carry their own per-file
license labels (CC BY 4.0 or ODbL, by bucket) as described in
[docs/DATA-LICENSES.md](docs/DATA-LICENSES.md).
