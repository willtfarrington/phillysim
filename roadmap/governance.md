# Governance: privacy, security, community, clinical, accessibility, maintenance

## Privacy

- v1 uses only authorized public aggregate/facility data and synthetic
  fixtures. No PHI, patient addresses, encounter data, credentials, or
  private planning material may enter the public system or repository.
  `required roadmap decision`
- HIPAA does not apply to this public civic-data product and the project
  never claims "HIPAA compliance"; privacy protections (below) are applied
  because they matter, not because a statute compels them. Any future
  identifiable-data ambition requires institutional sponsorship, formal
  review, and a separately governed private track — it is not a roadmap item.
- No address-entry or geolocation features. Deep links encode viewport/tract
  selection only; responsible-use microcopy notes that shared links reveal an
  area of interest. `required release evidence`
- Site privacy note (About page): hosted on GitHub Pages; GitHub logs visitor
  IP addresses per its privacy statement; the site itself sets no cookies,
  runs no analytics, and calls no third parties. `required release evidence`
- No suppression is needed for statistical privacy (methodology.md); mosaic
  and stigma risks are handled by language rules, non-ranking presentation,
  and the review gates below.

## Community safety & equity

- Non-ranking, assets-alongside-gaps presentation (see quality gates and UX
  plan); people-first language per a maintained style sheet; no police/crime
  proxies in v1.
- **Pre-publication impact review** `required release evidence`: before the
  demo ships, a documented review of stigma, misuse (redlining/resource-
  withdrawal readings), sensitive-site exposure, and claims compliance.
- **Delisting/takedown policy** `required release evidence`: any listed
  site/organization may request removal via the correction channel; response
  is an expedited rebuild of the site and public data files within a stated
  window and a changelog note; safety-motivated requests additionally trigger
  retraction/re-issue of affected release artifacts (raw snapshots retained
  privately for reproducibility, no longer republished).
- Correction/feedback channel: GitHub Issues (data-correction template) +
  public contact email; best-effort triage, no SLA; corrections affecting
  published aggregates bump the data snapshot or metric version.
- Volunteering/advocacy pathways route through established organizations
  (link-outs, e.g., to the Share Food Program's own locator — the project
  never builds a live locator and never directs outreach at households).
- Compensated stakeholder review and right-of-reply are promotion criteria
  for any future ranking/advocacy-adjacent feature — deliberately not v1
  obligations for a non-ranking descriptive atlas. `required roadmap
  decision`

## Clinical safety

- Aggregate-only, forever, absent a separately governed institutional track.
  The claims matrix (charter.md) is enforced at the release gate.
- Clinically framed narrative (e.g., context on diet-sensitive conditions) is
  flagged for informal expert review (dietitian colleague) before the public
  demo; if review is unavailable, the narrative is held out and the tool
  ships without it. `conditional artifact with trigger`
- Store-category vocabulary is format-based; nutrition-quality adjectives on
  project-derived classifications are prohibited (claims matrix row).

## Accessibility `required release evidence`

WCAG 2.2 AA target. The synchronized HTML table + narrative view is the
declared assistive-technology-primary path (canvas maps are opaque to AT) and
is maintained at full parity via a shared data pipeline and a release-gate
checklist. Automated axe checks in CI; **manual keyboard-only and NVDA
screen-reader pass is a release gate**, documented in the repo. Color is
never the sole carrier; CVD-safe 5-class binned palette; reduced-motion
honored; 320 px reflow; plain-language explainers beside every metric.

## Legal-review and expert-review flags (honest gaps)

This is a solo public-interest project without retained counsel. Items a
qualified reviewer would strengthen, tracked visibly rather than papered
over: City license interpretation (confirmed in writing by the Open Data
Program's office on 2026-09-02, OQ-A; the formal license text is unchanged);
ODbL bucket boundaries (conservative reading adopted); claims-matrix wording
(clinical colleague review planned). Disclaimers are not treated as curing
unsafe design; where meaningful review is infeasible, the default is coarser
presentation or omission.

## Maintenance & archival

- Post-v1 posture: maintained snapshot. Roughly quarterly dependency/source-
  terms review; data refresh only when chosen, via the controlled refresh
  workflow (terms re-read, drift check, snapshot bump, changelog).
- Dependency policy: uv lock + Dependabot; JVM and R5 jar pinned by checksum;
  pinned CI actions.
- Failure handling: corrupted snapshot/cache → re-acquire by manifest or
  restore from retained raw zone; upstream source vanishes → published
  derived tables keep releases reproducible (scoped claim), row updated in
  sources.md, feature removed or fallback invoked with changelog.
- Archival path: if development ends, the demo is frozen with a visible
  "as of" vintage banner, the repo is marked archived with a status note,
  and the delisting channel remains monitored best-effort or the map layer
  taken down. `required roadmap decision`
- Exposure response: accidental secret/data commit → rotate/revoke, purge
  history, document; prevention via scanning + push protection.
