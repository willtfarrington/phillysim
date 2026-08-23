# Scope: v1, v1.x, v2

Strategy: **shared geospatial core + one flagship module** (nutrition-resource
access). Depth, validity, and an end-to-end demonstration over breadth.
`required roadmap decision`

## v1 scope (MoSCoW)

| Item | Priority |
|---|---|
| Governed public repo (hygiene, licenses, claims, disclosure) | Must |
| Snapshot/manifest pipeline, zones, drift detection, offline CI fixture | Must |
| 2020-tract spine (TIGER 2025 + CenPop2020) + ACS 2020–2024 denominators/MOE | Must |
| Destination layers: SNAP-retailer supermarket-format points, farmers' markets, free food & meal sites | Must |
| Network walk travel times (OSM); walk+transit (SEPTA GTFS) via r5py | Must (transit degradable via spike kill criteria) |
| Baseline access metrics + MOE propagation + reliability flags | Must |
| Two-tier proximity vs open-when-reachable metrics (category-aware) | Must |
| Validation vs USDA SRAM (like-for-like all-SNAP-retailer variant) | Must |
| Static MapLibre site + full-parity table/narrative + methods/data cards | Must |
| WCAG 2.2 AA + manual NVDA/keyboard release gate | Must |
| CSV export (license-labeled, injection-safe), deep-link state | Should |
| Public-domain minimal basemap (AM-5) | Must |
| Sensitivity runs published: threshold grid + slow-walk | Should |
| Saturday-window market metrics | Should |
| PNG export, reliability hatching, guided-tour page | Won't (cut-first list) |
| 2SFCA/gravity, PMTiles basemap | Won't (v1.x gated) |

**Thin vertical slice** (proves the whole chain early, M2): one source (SNAP
retailers) → snapshot → validate → normalize to tract spine → one trivial
metric (straight-line QA column) → public-safe GeoJSON → minimal page render.

## v1.x candidates (gated)

| Candidate | Promotion gate |
|---|---|
| PMTiles self-hosted basemap | Pages range-request smoke test passes (open bug re range requests on Pages); enhancement packet only |
| 2SFCA/gravity enrichment | Baseline-unanswerable planning question + real capacity data + travel-time validation passed + exposed weights & decay/catchment sensitivity |
| Pharmacy-access module (concept 1, access form only) | Five gated-module criteria below; pricing leg permanently descoped absent an expressly licensed price source |
| Additional nutrition sources; Saturday-headline market view | Source matrix rows complete; method-card updates |

## v2 candidates (each independently gated)

| Candidate | Gate |
|---|---|
| Telehealth/digital-access module (concept 3) | Five gated-module criteria; constructs separated (availability/adoption/affordability/devices/literacy/accessibility) |
| Scenario layer ("sim" earns meaning) | Methods + validation + claims review commensurate with counterfactual framing |
| Suburban/NJ catchment | Multi-vintage/source cost accepted; MAUP re-review |
| Multilingual (Spanish first) | Human translation review; never machine-only for clinically adjacent content |
| Police/crime data | Documented necessity/validity/bias/alternatives justification; individual disposition |
| Formal research output | Separately governed workstream |
| Compensated stakeholder review, right-of-reply | Required before any ranking/advocacy-adjacent feature; until then non-ranking presentation stands |

**Gated-module promotion criteria (all five required):** complete source-
feasibility matrix; construct-validity plan naming the module's traps; shared
core demonstrably reused; session capacity without destabilizing v1
maintenance; module-scoped harm/claims review. `required roadmap decision`

**Kill criteria:** routing spike kill → walk-only v1 (partial fallback
permitted: tract-origin transit may ship while block-group sensitivity is
demoted). A source whose terms change adversely → fallback per sources.md or
feature removal with changelog. A view that defeats non-ranking mitigation →
cut the view. No dietitian review available → clinical narrative held out of
the public demo (tool ships without it).
