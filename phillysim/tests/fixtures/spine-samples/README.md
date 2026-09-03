# spine-samples — real-shaped CI samples of the real sources

Fixture-scale subsets of the **real** snapshots acquired on 2026-09-02 (the
three spine sources, EP-5a; the USDA SNAP retailer file, EP-6; the TIGER
county roads file, EP-8b) and 2026-09-03 (the two routing sources, EP-12:
the OpenStreetMap extract, clipped, and SEPTA's GTFS feed, replaced by a
synthetic feed), so the source contracts
(`tests/contracts/test_spine_sources.py`, `test_snap.py`,
`test_tiger_roads.py`, `test_osm_network.py`, `test_septa_gtfs.py`) and the
real pipeline's stages (`tests/integration/test_real_pipeline.py`) run
offline in CI against the provider's own file shapes. Six of the seven are
not synthetic: every byte of data is Census Bureau, USDA, or OpenStreetMap
data, and the manifests say so (`synthetic: false`, a `license_note` that
names the subset); the GTFS sample is synthetic by rule (below).

## License

The five Census and USDA sources are works of the United States Government
and therefore in the **US public domain** (17 U.S.C. § 105). The Census
Bureau "publishes its data as open data, meaning it is freely available for
use and re-use by the public" (its Open Government page, archived as
`terms.html` beside every real Census snapshot and excerpted here), and the
TIGER/Line technical documentation (2025, section 1.2) states that
copyright protection is not available for the files and asks only that the
Census Bureau be cited as the source. USDA publishes the SNAP retailer file
as public data (docs/DATA-LICENSES.md records why no USDA terms page is
archived). Committing these subsets to the repository is therefore
permitted; they carry the same Bucket A label as the real snapshots
(ADR-0003). TIGER/Line® is a registered trademark of the Census Bureau;
nothing here repackages the files under another name.

**The `osm_network` sample is OpenStreetMap data.** It is made available
under the **Open Database License (ODbL) 1.0**
(https://opendatacommons.org/licenses/odbl/1-0/); the data are
**© OpenStreetMap contributors** (https://www.openstreetmap.org/copyright),
extracted by Geofabrik GmbH. The sample is the real dated extract clipped
to the bounds of the six sample tracts with the same way-complete clip the
`network` stage runs (`build_samples.py`); its manifest is the first Bucket
B manifest in the repository (`license_bucket: "B"`, `synthetic: false`),
and anything computed over it in the suite is ODbL by derivation. Nothing
here alters the data beyond the clip.

**The `gtfs` sample is synthetic and carries no SEPTA content.** SEPTA's
developer license agreement is revocable and the project never republishes
the feed (roadmap/sources.md, docs/DATA-LICENSES.md), so committing any
subset of the real feed would republish feed contents. The sample is a
feed in SEPTA's layout (an outer `gtfs_public.zip` holding `google_bus.zip`
and `google_rail.zip`) with stops placed on the six sample tracts'
population-weighted centers, one route and two services per feed, and the
pinned release's `feed_info.txt` dates; its manifest says
`synthetic: true`. The terms excerpt beside it is the two sentences of
SEPTA's agreement the adapter checks, quoted from the archived page.

## Layout

```
raw/<source>/<snapshot id>/          2026-09-02 for the five Census / USDA sources,
                                     2026-09-03 for osm_network and gtfs
  <data file(s)>      same file names, header, and record layout as the provider's
  terms.html          excerpt: the paragraph(s) or fragments the adapters check
                      (the real Census page is 311 KB)
  source-page.html    (snap_retailers) excerpt: the two fragments of the provider's data
                      page the adapter checks
  <file>.md5          (osm_network) the MD5 sidecar in Geofabrik's format, regenerated for
                      the sample's bytes
  manifest.json       built through phillysim.manifest; digests match the files here
```

| Source | Provider file(s) | Sample contents | After the filter |
|---|---|---|---|
| `tiger_tracts` | `tl_2025_42_tract.zip` (TIGER/Line 2025, Pennsylvania tracts, NAD 83) | a shapefile of 8 tracts with every TIGER attribute, zipped with fixed timestamps (the dBASE header's write date pinned too) | 6 tracts |
| `cenpop` | `CenPop2020_Mean_TR42.txt` (CenPop2020, Pennsylvania tract centers) | the provider's header (with its byte-order mark) and 8 rows, verbatim | 6 tracts |
| `acs` | `acsdt5y2024-b01003.dat`, `acsdt5y2024-b08201.dat` (ACS 5-year 2020–2024 table-based summary file) | the header, the nation and Pennsylvania rows, and 8 tract rows, verbatim | 6 tracts |
| `snap_retailers` | `snap-retailer-locator-data2005-2025.zip` (USDA SNAP Retailer Locator historical data, one CSV member) | the provider's header and 31 rows: the 26 retailers authorized as of 2025-12-31 whose points fall inside the six sample tracts, 2 closed Philadelphia spells, 2 open Adams County rows, 1 open Delaware row | 26 retailers (5 of them supermarket-format) |
| `tiger_roads` | `tl_2025_42101_roads.zip` (TIGER/Line 2025, Philadelphia County roads, NAD 83) | a shapefile of 52 road features with every TIGER attribute: the 48 primary and secondary roads (MTFCC S1100 / S1200) crossing the six sample tracts, plus 4 local-road control rows (S1400 / S1630) inside them; zipped with fixed timestamps, dBASE date pinned | 48 roads (9 primary, 39 secondary) |
| `osm_network` | `pennsylvania-260831.osm.pbf` (Geofabrik's dated Pennsylvania extract, WGS 84) + `.md5` sidecar | the extract clipped to the six sample tracts' bounds, way-complete (49,473 nodes, 11,532 ways, 46 restriction relations; 749 KB), the provider's header (generator, replication timestamp, the state's bounding box) carried over so the sample passes the same header contract as the real file; tags and metadata as delivered; ODbL, © OpenStreetMap contributors | one summary row; the `network` stage clips it again into the county box, whole |
| `gtfs` | `gtfs_public.zip` holding `google_bus.zip` and `google_rail.zip` (SEPTA's layout) | **synthetic**: 7 bus stops (the six tract centers plus one control stop in Adams County, outside the routing box) and 2 rail stops, one route and two services (weekday, Saturday) per feed, `feed_info.txt` with the pinned release's dates and version; zipped with fixed timestamps | two feed rows; the control stop is counted outside the box, not dropped |

The six Philadelphia County tracts are `42101000101`, `42101000102`,
`42101000200`, `42101000300`, `42101000401`, and `42101000403`; the two control
tracts, `42001030101` and `42001030103`, are in Adams County and exist so the
county filter demonstrably drops something. The ACS nation row carries a real
annotation value (`-555555555` as the MOE of a controlled estimate) and is
dropped as a non-tract row. The SNAP control rows exist so that each part of
that adapter's filter (state, county, open spell) demonstrably drops something;
the local-road control rows do the same for the roads adapter's feature-class
filter (the provider's county file needs no county filter); the GTFS control
stop shows that a stop outside the routing box is counted, never dropped.

## Regenerating

From `phillysim/`, after `phillysim run --stage spine` has admitted the pinned
snapshots into the data root and built the spine (the SNAP sample is cut by
point-in-tract against it, the roads sample by intersection with the sample
tracts, the OSM sample by the clip over the sample tracts' bounds, the GTFS
sample's stops placed on their centers); the OSM clip over the 346 MB state
extract takes a few minutes:

```
uv run python tests/fixtures/spine-samples/build_samples.py [--data-root DIR]
uv run pytest tests/contracts tests/test_destinations.py tests/test_basemap.py tests/test_network.py tests/integration/test_real_pipeline.py
```

`build_samples.py` is deterministic for a given real snapshot. Regenerate only
when a pinned snapshot changes (a controlled refresh changes that source's
entry in `phillysim.pipeline.SNAPSHOT_IDS`) and say so in the changelog.
`tests/fixtures/.gitattributes` keeps every file here byte-exact on checkout.
