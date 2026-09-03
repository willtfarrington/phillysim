# ADR-0007: The analysis CRS is NAD 83 / UTM zone 18N (EPSG:26918)

Status: accepted (EP-5b, 2026-09-02; owner-reviewed)

## Context
methodology.md pins "a single projected CRS for analysis, documented in the
data dictionary; WGS 84 only at the publication boundary" but leaves the
choice to the first packet that curates real geometry. The spine sources are
delivered on NAD 83: TIGER/Line 2025 tract polygons and CenPop2020 centers
both carry EPSG:4269 (ACS has no geometry). Everything downstream measures
in metres: county-bounds checks, geometric-versus-population-weighted
centroid distances, the M5 block-group sensitivity, straight-line fallbacks,
and area-based checks. Routing (r5py, M3) and the map (MapLibre, M6) take
geographic coordinates at their own boundaries. City of Philadelphia layers
(M4) arrive in the City's State Plane feet CRS. The choice affects every
later distance-bearing computation, so it is made once, here, with the
alternatives recorded.

## Decision
Every analysis-zone geometry (the curated spine and every table derived from
it) carries **EPSG:26918, NAD 83 / UTM zone 18N, metres**.

- Metres, so distances and areas need no unit conversion anywhere.
- The same datum as TIGER and CenPop, so reprojecting from the sources is a
  pure map projection with no datum transformation.
- Philadelphia County (75.28° W to 74.96° W) straddles zone 18's central
  meridian at 75° W, where the projection's distortion is smallest: the grid
  scale factor stays between 0.9996 and 0.99961 across the county, under
  0.04 percent of length, sub-metre over any tract.
- An EPSG code every tool in the stack resolves without a custom
  definition (pyproj, GeoPandas, DuckDB spatial, QGIS); GeoPandas'
  `estimate_utm_crs()` on NAD 83 input returns exactly this CRS, so it is the
  conventional choice for the datum, not a local one.

Where it is recorded: `phillysim.spine.ANALYSIS_CRS`; the `spine` stage's
`crs` parameter (fingerprinted, so changing it re-runs every downstream
stage); the GeoParquet metadata of every analysis-zone geometry column; the
data dictionary's "Conventions" and per-table notes. The invariant module
(`phillysim.spine.check_spine`) refuses any other CRS on the spine.

The population-weighted centers stay in the spine as the degrees CenPop
publishes (`centroid_lon`, `centroid_lat`, NAD 83): that is the form routing
origins take, and `phillysim.spine.centroids_in` is the one place that turns
them into projected points. Publication converts geometry with
`to_crs("EPSG:4326")` and nothing else.

## Alternatives considered
- **EPSG:2272, NAD 83 / Pennsylvania South (US survey foot).** The City of
  Philadelphia's own CRS; every City layer will arrive in it and convert
  losslessly. Rejected as the analysis CRS because of the unit: every
  distance would carry a feet-to-metres factor, and the US survey foot is
  itself deprecated.
- **EPSG:32129, NAD 83 / Pennsylvania South (metre).** The metric State
  Plane zone; Lambert conformal conic with distortion of the same order as
  UTM here. Equally sound. Not chosen because UTM 18N offers the same
  properties under a code that consumers recognise on sight, and no source or
  consumer of this project uses 32129; either would have served.
- **EPSG:6565 / 6564, NAD83(2011) Pennsylvania South.** TIGER labels its
  data NAD 83 without a realisation; adopting a 2011-realisation CRS would
  assert a precision the sources do not carry.
- **EPSG:3857, Web Mercator.** Scale factor about 1.3 at 40° N; a display
  projection, not a measurement one.
- **EPSG:4326 / 4269, geographic.** No metric distance or area; kept only at
  the delivery boundary (4269, as the sources arrive) and the publication
  boundary (4326).

## Datum note at the publication boundary
The public zone is WGS 84 (EPSG:4326). NAD 83 and WGS 84 differ by about one
metre in this region, and pyproj's transformation between EPSG:4269 and
EPSG:4326 without a stated realisation is the null transformation, so
published coordinates are the NAD 83 values relabelled. That is far below
tract-level relevance and is documented rather than "corrected".

## Consequences
Distance computations are Euclidean in metres on EPSG:26918 geometry.
Changing this CRS means changing `ANALYSIS_CRS` and the stage parameter,
superseding this ADR, and bumping the methods version (ADR-0006: it is a
pinned parameter). The tinycity fixture, a synthetic grid placed off the
Atlantic coast outside zone 18, keeps its own geographic CRS through the
fixture pipeline's `crs` parameter; the invariant module takes the expected
CRS as an argument for that reason.
