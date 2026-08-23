# Charter

## What this is

phillysim is a local-first, public-interest civic-data project that measures
access to health-relevant community resources — v1: food resources relevant to
patients managing diet-sensitive chronic conditions — across Philadelphia
County at the 2020 census-tract level, and presents the results in an
accessible public map, table, and narrative.

**On the name:** "sim" is aspirational lineage with the author's sibling
projects, not a claim. v1 contains no simulation. A scenario layer (e.g.,
"what changes if a site closes?") may only be added if a future evidence gate
(scope.md §v2) is passed; until then the project describes, it does not
simulate, predict, or prescribe. The repository tagline and description say
"measuring access," not "modeling outcomes."

## Who it is for, and for what

- **Primary user:** the author and similarly situated hospitalist clinicians,
  for *aggregate, locality-aware* planning: preparing discharge-education
  materials and social-work briefings that reflect the real resource
  landscape patients return to, and identifying vetted community-partnership
  opportunities. `required roadmap decision`
- **Secondary audiences:** technical readers evaluating the engineering and
  methods; community-facing readers exploring Philadelphia food access.

Five design-target scenarios (education-material planning by catchment
tract-set; social-work briefing preparation; assets-first partnership
scouting; feasibility-aware framing of diet education, narrative-only;
geography orientation for new clinicians) are documented with literature
grounding in the methods/data cards. Every scenario ends in a conversation or
document, so exportable tract-set summaries with vintage, uncertainty, and
limitations attached are first-class features.

## Prohibited uses and non-goals (charter-level)

No patient-specific tools or advice. No clinical decision support, patient
flagging, or EHR integration absent separate institutional ownership of
validation, safety, privacy, and regulatory obligations. No hosted backend
service. No medication courier/delivery planning. No direct unvetted outreach
to households. No police/crime data in v1 (gated post-v1 with a mandatory
necessity/validity/bias/alternatives justification). No predictive, causal,
or outcome claims. No multi-city scope in v1. No real-time data. No PHI and
no address-entry workflows in the public system, ever, absent a separately
governed private track. Area-level measures are never presented as individual
risk. `required roadmap decision`

## Claims discipline

A claims matrix (docs/CLAIMS.md at implementation; `required release
evidence`) maps every public claim to evidence and permitted wording. Anchor
rows include:

- The project **measures access**; it does not diagnose "food deserts,"
  measure food insecurity, or evaluate diet quality.
- Access ≠ affordability ≠ inventory ≠ suitability. Store categories are
  format-based ("SNAP-authorized supermarket-format"); nutrition-quality
  adjectives are prohibited on project-derived classifications.
- The project **publishes no scores, composite indices, or ranked lists**;
  tables are user-sortable, and sorted views carry margin-of-error caveats.
- Associations are never described as causation; neighborhood measures never
  as individual risk.
- Clinical relevance is conveyed by cited narrative context only, reviewed
  before public release (governance.md); intervention-outcome literature
  (e.g., medically tailored meal trials) is cited only in partnership
  context, never as what the map "supports."
- Utility claim ceiling: "informed the author's own planning" — no usage,
  adoption, or outcome claims.

## Success evidence for v1 `required release evidence`

1. Reproducible pipeline: fresh clone → documented commands → checksum-
   identical outputs within the pinned environment (canonicalized-value
   hashes cross-platform); reproducible from source while upstream terms and
   availability persist, otherwise from published derived tables.
2. Every published metric traceable to source + method card, with uncertainty
   and limitations displayed beside results.
3. The public demo passes the pre-publication harm/claims review and the
   manual keyboard/screen-reader accessibility gate.
4. At least one concrete, self-reported planning insight from the author's
   own practice context.

## Publication & portfolio plan

- README narrative: problem → data → methods → limits → demo, project-
  centered, no affiliation implications, with an architecture/data-lineage
  visual and screenshots. `required release evidence`
- Method cards and data cards per metric/source; limitations and
  responsible-use statement; changelog and tagged releases. `required release
  evidence`
- Static public demo (GitHub Pages) published only after the review gates.
  `required release evidence`
- Benchmarks from the routing spike; personal-site handoff blurb/imagery.
  `optional portfolio enhancement`
- One dated community-context document (the Philadelphia food-access org
  landscape is volatile; facts live in one place, not scattered in UI).
  `required release evidence`
