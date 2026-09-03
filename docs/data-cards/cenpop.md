# Data card: CenPop2020 tract centers of population (`cenpop`)

**Contributes.** Two things the spine cannot get elsewhere: the **2020
Census population** of every tract (a complete count, no sampling margin of
error) and the **population-weighted center** of each tract, which is the
routing origin methodology.md pins ("Units and origins"). The project never
recomputes a center from tract geometry: a geometric centroid would put the
origin of a river tract in the water and the origin of a half-empty tract in
its empty half.

**Provider and file.** US Census Bureau, Centers of Population for the 2020
Census, by census tract, Pennsylvania: `CenPop2020_Mean_TR42.txt` from
`https://www2.census.gov/geo/docs/reference/cenpop2020/tract/` (comma
separated, UTF-8 with a byte-order mark; one row per 2020 tract with FIPS
codes, population, latitude, longitude).

**Vintage.** 2020 Census (April 1, 2020) population on 2020 tract
definitions. Pinned snapshot `2026-09-02`; a controlled refresh (there will
be none until the 2030 Census) bumps this source's entry in
`phillysim.pipeline.SNAPSHOT_IDS` (snapshot IDs are per source since EP-12).

**Terms and license.** US public domain (17 U.S.C. § 105); the Open
Government page in force archived as `terms.html`. **Bucket A** (ADR-0003).
Citation: "U.S. Census Bureau, Centers of Population by Census Tract, 2020
Census, Pennsylvania".

**Coverage and filter.** Delivered per state; stored as delivered and
filtered at first read to `STATEFP = 42`, `COUNTYFP = 101`; the eleven-digit
`geoid` is derived from the FIPS columns.

**CRS.** Latitude and longitude in NAD 83 (EPSG:4269), as delivered. The
spine keeps them as published (`centroid_lon`, `centroid_lat`, degrees), the
form routing origins take; `phillysim.spine.centroids_in` projects them into
the analysis CRS EPSG:26918 (ADR-0007) when a distance is needed. WGS 84
only at the publication boundary.

**Where it lands.** `curated/tracts_spine.parquet` (`population`,
`centroid_lon`, `centroid_lat`; data dictionary, "Curated tract spine").

**Known limits (real snapshot, 2026-09-02).**
- Five tracts have **zero** 2020 population (`42101980400`, `42101980701`,
  `42101980902`, `42101980905`, `42101980906`: the airport, port, and park
  `980x` series). The file still carries a center for them; population
  weighting makes them contribute nothing to population-weighted results,
  and the metrics stage decides how to display them (M5).
- A population-weighted center can fall **outside its own tract** when the
  tract is concave or its population sits at the edges; five do
  (`42101037300`, `42101037800`, `42101980100`, `42101980200`,
  `42101980800`), the farthest by 316 m. This is correct behaviour of a mean
  center and is why the invariants check the county bounds, not containment
  in the tract.
- The mean center is the population-weighted mean of 2020 block centers, so
  it is an aggregation, not a place anyone lives at; the M5 block-group
  sensitivity (methodology.md) measures how much that aggregation moves
  tract-level results.
- Population counts are the 2020 Census as published, including the
  Bureau's disclosure-avoidance noise at block level; at tract level the
  effect is small, and the counts are complete-count figures with no
  sampling margin of error, which is why the spine marks them as such.

**Claims matrix.** Population is a denominator and a weight, never a score
(C-3). Nothing here describes individuals (C-4).

**Checks that bind it.** Source contract (`phillysim.adapters.cenpop`), the
invariants (exactly one center per spine tract and none unmatched; every
center inside the county bounds), and the snapshot manifest.
