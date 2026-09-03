# Claims matrix

Every public claim the project makes — in the README, site copy, method/data
cards, exports, and release notes — must trace to a row here. Row wording is
taken **verbatim** from [roadmap/charter.md](../roadmap/charter.md) ("Claims
discipline"); this file adds enforcement notes and permitted/prohibited
phrasing but never relaxes a charter row. Conflicts are resolved by amending
charter.md first, then this file.

Compliance with this matrix is checked in the pre-publication harm/claims
review ([roadmap/governance.md](../roadmap/governance.md)) and the release
checklist ([roadmap/quality.md](../roadmap/quality.md)).

## Anchor rows (charter.md, verbatim)

| ID | Rule (verbatim from charter.md) |
|---|---|
| C-1 | The project **measures access**; it does not diagnose "food deserts," measure food insecurity, or evaluate diet quality. |
| C-2 | Access ≠ affordability ≠ inventory ≠ suitability. Store categories are format-based ("SNAP-authorized supermarket-format"); nutrition-quality adjectives are prohibited on project-derived classifications. |
| C-3 | The project **publishes no scores, composite indices, or ranked lists**; tables are user-sortable, and sorted views carry margin-of-error caveats. |
| C-4 | Associations are never described as causation; neighborhood measures never as individual risk. |
| C-5 | Clinical relevance is conveyed by cited narrative context only, reviewed before public release (governance.md); intervention-outcome literature (e.g., medically tailored meal trials) is cited only in partnership context, never as what the map "supports." |
| C-6 | Utility claim ceiling: "informed the author's own planning" — no usage, adoption, or outcome claims. |

## Enforcement notes and wording guidance

### C-1 — measurement, not diagnosis

- Permitted: "measures access," "travel time to," "counts within X minutes,"
  "access measure," "descriptive atlas."
- Prohibited: "food desert," "food insecure," "food insecurity rate,"
  "healthy/unhealthy food environment," "diet quality," and any construct the
  data do not measure.
- Evidence basis: metric definitions in
  [roadmap/methodology.md](../roadmap/methodology.md); each published metric
  has a method card naming exactly what it measures.

### C-2 — construct separation and format-based vocabulary

- Store-category vocabulary comes from the published USDA store-type mapping
  and is format-based only (e.g., "SNAP-authorized supermarket-format
  store," "farmers' market," "free food & meal site").
- Prohibited on project-derived classifications: "healthy," "nutritious,"
  "quality," "good/bad food," or any nutrition-quality adjective.
- Access results are never presented as statements about affordability,
  stocked inventory, or dietary suitability.

### C-3 — no scores, no rankings

- No composite index, no weighted score, no "top/bottom N tracts" view is
  published. Components are exposed individually.
- Table sorting is a user action; sorted views display margin-of-error
  caveats (reliability flags per methodology.md).

### C-4 — no causation, no individual risk

- Permitted: "tracts where measured travel time is longer," "is associated
  with" only when citing external literature that itself claims association.
- Prohibited: "causes," "leads to," "puts residents at risk," or applying any
  tract-level measure to an individual person.
- Ecological-inference limits are displayed beside results, not buried
  (methodology.md, "Fairness & validity limits").

### C-5 — clinical narrative is cited context, gated by review

- Clinically framed narrative ships only after the informal expert review
  described in governance.md; if review is unavailable, the narrative is held
  out and the tool ships without it.
- Intervention-outcome literature is cited only in partnership context —
  never phrased as evidence of what this map "supports" or achieves.

### C-6 — utility ceiling

- The strongest permitted utility statement is that the project "informed the
  author's own planning."
- Prohibited: user counts, adoption claims, health-outcome claims, or
  testimonial framing beyond the author's own self-report.

## Standing prohibitions (charter.md, "Prohibited uses and non-goals")

The charter's prohibited-uses list binds all public content: no
patient-specific tools or advice; no clinical decision support, patient
flagging, or EHR integration; no hosted backend service; no direct unvetted
outreach to households; no predictive, causal, or outcome claims; no PHI and
no address-entry workflows in the public system. Area-level measures are
never presented as individual risk. See charter.md for the full list and its
conditions.

## Mechanical enforcement (EP-7)

The publish gate (`phillysim.publish.gate`) applies the parts of this matrix
a program can check to every public data file: column and property names
must be lowercase slugs carrying none of `healthy`, `unhealthy`,
`nutritious`, `quality`, `desert`, `insecur`, `score`, `rank`, or `index`
(C-1, C-2, C-3), and any column whose metric ID starts with `qa_` must be
declared quality-assurance-only with a description that says so, beside a
manifest note that QA columns are not access measures
([methodology.md](../roadmap/methodology.md) "Travel model"). Prose, cards,
and site copy remain the manual sweep's job.

## Maintaining this file

- New public claims require a new row (or an amendment to an existing row)
  **before** the claim ships.
- Wording changes to anchor rows happen in charter.md first; this file
  mirrors them.
- The release checklist's claims-compliance sweep records the reviewed
  version of this file in the release notes.
