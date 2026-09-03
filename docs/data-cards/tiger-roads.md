# Data card: TIGER/Line 2025 roads, primary and secondary (`tiger_roads`)

**Contributes.** The roads of the minimal public-domain basemap
([ADR-0005](../../roadmap/adr/0005-basemap-public-domain-first.md)): the
county's primary roads (interstates and other limited-access highways) and
secondary roads (US, state, and county highways and the main arterials),
drawn in gray beneath the tract outlines so the map has orientation. That is
all it contributes: no metric reads it, no destination is located on it, and
the routing network (M3) comes from OpenStreetMap, not from this file.

**Provider and file.** US Census Bureau, TIGER/Line Shapefiles 2025, roads
layer for Philadelphia County (the Bureau distributes roads per county):
`tl_2025_42101_roads.zip` from
`https://www2.census.gov/geo/tiger/TIGER2025/ROADS/`, 1,352,071 bytes. The
shapefile is read straight from the zip (pyogrio); nothing is extracted.

**Vintage.** Road features as of 2025-01-01 (the 2025 TIGER/Line release).
Pinned snapshot `2026-09-02` (this source's entry in
`phillysim.pipeline.SNAPSHOT_IDS`; snapshot IDs are per source since EP-12,
and the five sources acquired on 2026-09-02 keep that date); a controlled
refresh bumps that entry and is recorded in the changelog
(roadmap/sources.md).

**Terms and license.** A work of the United States Government, US public
domain (17 U.S.C. § 105); the Census Bureau publishes its data as open data
and asks to be cited as the source; TIGER/Line® is a registered trademark of
the Bureau (technical documentation 2025, section 1.2). The Open Government
page in force is archived as `terms.html` beside the snapshot, as for the
tract file. **Bucket A** (CC BY 4.0 for derived prose and tables; ADR-0003).
Citation: "U.S. Census Bureau, TIGER/Line Shapefiles 2025, roads".

**Coverage and filter.** The provider's file is already county-scoped, so
the county filter of the other TIGER adapters becomes a **feature-class
filter** here: stored as delivered (so the snapshot verifies against the
provider) and filtered at first read to MTFCC `S1100` (primary) and `S1200`
(secondary). The local streets (`S1400`, about 9,000 features), ramps,
service drives, alleys, and walkways in the same file are dropped at the
read and never leave the raw zone. The pinned snapshot yields **426** major
roads (46 primary, 380 secondary; 9 interstate, 27 US, 60 state, and 330
common-name route types; every one named), 1,044 km in all, none of it
outside the county's tracts (the `basemap` stage measures that and records
it in `intermediate/basemap.json`).

**CRS.** Delivered in NAD 83, EPSG:4269. The `basemap` stage reprojects
into the analysis CRS **EPSG:26918** (NAD 83 / UTM zone 18N, metres;
[ADR-0007](../../roadmap/adr/0007-analysis-crs.md)), a pure projection with
no datum shift; the public file is WGS 84 at six decimals, like every
published geometry.

**Where it lands.** `curated/basemap_roads.parquet` (`linearid`, `name`,
`mtfcc`, `route_type`, `geometry`; data dictionary, "Basemap roads layer"),
and from there the `roads` layer of `public/basemap.geojson` (public schema
version 2), beside the county boundary the `publish` stage dissolves from
the spine.

**Known limits.**
- The two classes are the Bureau's, not a traffic or importance ranking:
  MTFCC assigns a road to a class by its function in the Bureau's own
  feature-class scheme. A busy arterial coded `S1400` is absent; a quiet
  state route coded `S1200` is present.
- Roads are cartographic centerlines generalized for statistical use, not
  survey-grade; bridges over the Delaware end at the state line, and
  limited-access carriageways may appear as one line or two.
- The feature count depends on how the Bureau segments a road (one
  `LINEARID` per named linear feature within the county), so the number of
  features is not a count of roads in any everyday sense; the length is
  the meaningful total.
- A later TIGER vintage may re-segment, rename, or reclassify features
  without any change on the ground; the pinned snapshot is what every
  result reproduces from.

**Claims matrix.** A basemap layer makes no claim about anything: it is
orientation for the eye. Nothing about access, travel time, distance, or
any tract is derived from it (C-1 through C-4 are untouched), and no
accessibility statement rests on it. It is drawn in gray at 3:1 or better
against the palette's lightest class, the map ground, and the county
boundary (the measured table is in `site/README.md`); color is never the
only carrier on the page.

**Checks that bind it.** Source contract (`phillysim.adapters.tiger_roads`:
unique `LINEARID`, `MTFCC` within the two classes, `RTTYP` within the
TIGER vocabulary, lines in NAD 83 inside the county bounds), the layer
invariants (`phillysim.basemap.check_roads`: CRS as declared, unique
identifiers, valid non-empty lines inside the county bounds, every road
touching the spine), the publish gate's basemap rules (declared layers and
counts, lines for the roads), and the snapshot manifest (`phillysim verify`).
