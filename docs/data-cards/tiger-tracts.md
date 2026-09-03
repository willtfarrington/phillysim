# Data card: TIGER/Line 2025 census tracts (`tiger_tracts`)

**Contributes.** The geometry of the spine: the boundary polygon and the
display name of each of Philadelphia County's 408 2020-vintage census
tracts. Nothing else in the project draws a tract outline from any other
source.

**Provider and file.** US Census Bureau, TIGER/Line Shapefiles 2025, tract
layer for Pennsylvania: `tl_2025_42_tract.zip` from
`https://www2.census.gov/geo/tiger/TIGER2025/TRACT/`. The shapefile is read
straight from the zip (pyogrio); nothing is extracted.

**Vintage.** Tract boundaries as of 2025-01-01 for the **2020** census
tracts (the 2020 tract definitions, with the Bureau's annual boundary
maintenance up to that date). The `GEOID` values are the 2020 tract
identifiers every other source in the spine joins on. Pinned snapshot
`2026-09-02` (`phillysim.pipeline.SNAPSHOT_ID`); a controlled refresh bumps
that constant and is recorded in the changelog (roadmap/sources.md).

**Terms and license.** A work of the United States Government, US public
domain (17 U.S.C. § 105); the Census Bureau publishes its data as open data
and asks to be cited as the source; TIGER/Line® is a registered trademark of
the Bureau (technical documentation 2025, section 1.2). The Open Government
page in force is archived as `terms.html` beside the snapshot. **Bucket A**
(CC BY 4.0 for derived prose and tables; ADR-0003). Citation: "U.S. Census
Bureau, TIGER/Line Shapefiles 2025, census tracts, Pennsylvania".

**Coverage and filter.** Delivered per state; stored as delivered (so the
snapshot verifies against the provider) and filtered at first read to
`STATEFP = 42`, `COUNTYFP = 101`. Every TIGER attribute survives the read;
the spine keeps `GEOID`, `NAMELSAD`, and the geometry.

**CRS.** Delivered in NAD 83, EPSG:4269. The `spine` stage reprojects into
the analysis CRS **EPSG:26918** (NAD 83 / UTM zone 18N, metres; ADR-0007), a
pure projection with no datum shift. WGS 84 only at the publication boundary.

**Where it lands.** `curated/tracts_spine.parquet` (`geoid`, `name`,
`geometry`; data dictionary, "Curated tract spine").

**Known limits.**
- Tract boundaries follow legal and statistical lines, water included:
  Philadelphia's river tracts (`980x` series) carry large water areas and
  little or no population. The spine keeps them; population weighting
  (CenPop) and the metrics decide what they mean.
- TIGER is the Bureau's cartographic file, generalized for statistical use;
  it is not a survey-grade parcel boundary. At tract scale this is
  irrelevant; do not use it to decide which side of a street a point is on.
- Boundary maintenance means a later TIGER vintage may move a line by a few
  metres without changing the 2020 GEOIDs; the pinned snapshot is what every
  result reproduces from.

**Claims matrix.** A boundary file makes no claim about people. Results
attached to a tract are area-level measures and are never applied to an
individual (C-4). The spine is not a ranking of tracts (C-3).

**Checks that bind it.** Source contract (`phillysim.adapters.tiger`), the
geospatial invariants (`phillysim.spine.check_spine`: valid polygons, county
bounds, 2020 GEOID pattern, count of 408), and the snapshot manifest
(`phillysim verify`).
