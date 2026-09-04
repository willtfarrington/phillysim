# Geospatial & statistical methodology

Full parameter conventions were fixed in Planning Baseline v1.0 after
specialist research and red-team review; method cards restate them beside
results at publication. `required release evidence`: method card per metric.

## Units and origins

- Canonical unit: 2020 census tract (~408 tracts), Philadelphia County only.
- Origins: 2020 Census population-weighted tract centroids (CenPop2020).
- Mandatory sensitivity: block-group population-weighted centroids aggregated
  to tract, giving an empirical aggregation-error estimate (MAUP mitigation).
- CRS: a single pinned projected CRS for analysis (documented in the data
  dictionary); WGS84 only at the publication boundary. Chosen in EP-5b:
  EPSG:26918, NAD 83 / UTM zone 18N, metres
  ([ADR-0007](adr/0007-analysis-crs.md)).

## Destination layers

- SNAP-authorized supermarket-format stores (from the USDA store-type field;
  mapping published in the method card; OSM `shop=supermarket` cross-check).
- Farmers' markets (day + season aware).
- Free food & meal sites (structured per-day hours).
- Category vocabulary is format-based; nutrition-quality adjectives are
  prohibited on project-derived classifications.

## Travel model

- Engine: r5py (Conveyal R5), pinned JDK 21 and checksummed R5 jar, 12 GB
  heap; CPU-only.
- Modes: network walk (4.8 km/h; 3.0 km/h slow-walk sensitivity for mobility
  equity) and walk+transit (SEPTA GTFS).
- Departure convention: pinned typical Wednesday, 08:00–20:00, one departure
  per minute; travel-time distribution summarized as **typical time (median
  departure)** and **time on slower departures (85th percentile)** — the
  phrase "reliable access" appears only in prose with its definition.
- Saturday window computed for market-relevant metrics; weekday-window market
  exclusions labeled explicitly.
- Straight-line distance is computed only as a QA column, never published as
  an access measure.
- Fallback (spike kill): OSMnx 2.x + scipy sparse Dijkstra walk-only; partial
  fallback permitted.

## Metrics (transparent baseline family)

Per tract × category: time-to-nearest (censored at 120 min); counts within
15-min walk and 30-min walk+transit (threshold sensitivity grid 10–45 min
available; v1 publishes the two sensitivity runs feeding public claims —
threshold grid and slow-walk); population-weighted variants. Components are
exposed; no composite index is published.

**Two-tier labeling:** Tier 1 *proximity* (site exists) vs Tier 2
*open-when-reachable* (site open at arrival-feasible hours). Tier 2 is
**category-aware**: farmers' markets count if open on ≥1 day of the pinned
analysis week; meal sites use their structured daily hours. Pinned analysis
weeks: in-season (first full week of June) headline for seasonal categories,
off-season (first full week of February) sensitivity — both disclosed.
Hours-coverage percentage (how many sites had parseable hours) is published
with every Tier 2 metric; the market hours parser ships with a QA report.

## Uncertainty

ACS margin-of-error propagation per the Census ACS handbook's approximation
formulas for derived estimates; decennial-weighted quantities carry no
sampling MOE (differential-privacy noise documented instead). Stored as
first-class columns; coefficient-of-variation reliability tiers at 12% / 40%
drive a three-tier reliability flag (table symbol + detail-panel interval +
plain-language range sentence). Schema carries {estimate, MOE, CV tier,
reliability_action ∈ {none, interval-only}} per tract-metric; class bins are
computed at build time so map, table, and CSV agree.

## Suppression position `required roadmap decision`

No privacy-based small-cell suppression: all inputs are public aggregate or
public facility data, so suppression would protect nothing while degrading
transparency. Instead: reliability flags for statistical instability,
mosaic-framing language rules, and the published rationale in the methods
documentation. (Provider-suppressed upstream values, if any, remain missing —
never imputed or reverse-engineered.)

## Validation

- Like-for-like external comparison: the project's all-SNAP-retailer
  proximity variant vs USDA SRAM (same universe, same 2020-tract geography).
  The supermarket-class metric's external check is **unavailable in v1** and
  the method card says so; an LRAM/crosswalk comparison is optional and
  directional only.
- Known-answer tests on the synthetic fixture; spot-check gates (≥95% finite
  pairs; ≥80% of hand-checked OD times within tolerance; walk-network
  concordance ρ ≥ 0.95 vs fallback engine). *Reading fixed at EP-15 (owner
  decision, 2026-09-03):* the finite-pairs gate is read on the walk+transit
  core run; the walk-only run is reported against the straight-line reach
  bound the 120-minute censor allows (a 4.8 km/h walk covers 9.6 km; the
  county spans about 27 km), since no engine can reach 95 % of all pairs on
  foot under that censor, and every origin must reach at least one
  destination.
- Face-validity review against PDPH's published Neighborhood Food Retail
  analysis (prior art; cited and complemented, not claimed as novel ground).

## Fairness & validity limits (displayed, not buried)

Car-free assumption stated; slow-walk sensitivity addresses mobility limits;
seasonal markets handled by the category-aware tier; MAUP addressed by
tract-only reporting plus the aggregation sensitivity; ecological-inference
limits stated beside results (area measures never individual risk); temporal
mismatch between vintages disclosed per metric. 2SFCA/gravity remains gated
(scope.md) with exposed weights and decay/catchment sensitivity required at
promotion.
