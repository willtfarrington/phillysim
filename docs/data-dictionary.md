# Data dictionary

> **Status: seeded (EP-3); first real instances (EP-5b, EP-6, EP-7, EP-8b,
> EP-12).** Schema version **1**; public schema version **2** (EP-7 wrote
> version 1; EP-8b added the basemap file). This document describes the
> tables the pipeline produces. Instances today: the synthetic tinycity
> fixture's golden files (`phillysim/tests/fixtures/tinycity/`) for every
> curated table, and, since EP-5b, EP-6, EP-7, EP-8b, and EP-12, the real
> curated tract spine, its ACS join, the SNAP retailer layer, the basemap
> roads layer, the analytic table (holding the QA-only slice metric), the
> gated public zone, and the routing inputs (`intermediate/network/`: the
> clipped OSM extract and the two SEPTA feed zips) in the gitignored data
> root.
> The integer schema version is one of the manifest-recorded version axes
> ([ADR-0006](../roadmap/adr/0006-versioning-axes.md)): any breaking change to
> a table shape below bumps it, with a migration note here. Column names are
> format-based and carry no nutrition-quality adjectives
> ([docs/CLAIMS.md](CLAIMS.md)).

Conventions: `geoid` is the eleven-digit 2020 census-tract GEOID (state +
county + tract). Times are minutes. Nullable columns say so; everything else
is required.

**Coordinate reference systems.** The analysis CRS is **EPSG:26918, NAD 83 /
UTM zone 18N, metres** ([ADR-0007](../roadmap/adr/0007-analysis-crs.md)),
pinned in `phillysim.spine.ANALYSIS_CRS` and in the `spine` stage's `crs`
parameter. Which tables carry which CRS:

| Tables | CRS | Why |
|---|---|---|
| Raw-source tables (`raw/tiger_tracts`, `raw/cenpop` below) | NAD 83, EPSG:4269 | as delivered by the Census Bureau; never rewritten |
| Raw SNAP retailer table (`raw/snap_retailers` below) | WGS 84, EPSG:4326 | the provider's geocodes carry no stated datum; treated as WGS 84 (the difference from NAD 83 is far below the geocoding error) |
| Routing inputs: the OSM extract and its clip (`raw/osm_network`, `intermediate/network/`), the GTFS stops (`raw/gtfs`; EP-12) | WGS 84, EPSG:4326 | OpenStreetMap and GTFS coordinates are WGS 84 by definition and R5 reads both directly; the routing box (county bounds + 5 km) is computed in the analysis CRS and expressed in WGS 84 for the clip and the stop check |
| Curated tract spine `geometry`; every analysis-zone geometry derived from it or joined to it (the SNAP retailer layer since EP-6, sites, travel-time inputs, metrics) | EPSG:26918 | the analysis CRS; recorded in each GeoParquet file's metadata |
| `centroid_lon` / `centroid_lat` in the spine; `longitude` / `latitude` in the SNAP retailer layer and the sites table | degrees (NAD 83 as published for the spine, the provider's geocodes for destinations; treated as WGS 84 at publication, ADR-0007 datum note) | the form routing origins and destinations take; `phillysim.spine.centroids_in` projects the spine's centers on demand |
| Public zone (`public/`, GeoJSON / CSV; EP-7) | WGS 84, EPSG:4326 | the publication boundary, and nowhere else: the `publish` stage reprojects from the analysis CRS, rounds coordinates to six decimals, and writes RFC 7946 GeoJSON (no `crs` member, which the publish gate rejects) |
| The tinycity fixture's tables | the fixture's own geographic CRS (EPSG:4326, the fixture pipeline's `crs` parameter) | a synthetic grid outside Pennsylvania and outside UTM zone 18; the invariant module takes the expected CRS as an argument for this reason |

## Snapshot manifest (`raw/<source>/<snapshot-id>/manifest.json`)

Owned by the manifest engine (`phillysim.manifest`, EP-4a). Every field is
required; a manifest with a missing, extra, or malformed field is rejected
and the snapshot is quarantined. The file is canonical JSON (two-space
indent, keys sorted, UTF-8, trailing newline), so reading it and writing it
back reproduces the bytes exactly. It is the only place the manifest-recorded
version axes of [ADR-0006](../roadmap/adr/0006-versioning-axes.md) live.

| Field | Type | Meaning and rule |
|---|---|---|
| `source` | string | Source identifier; lowercase slug `[a-z][a-z0-9_]*`; must equal the parent directory name |
| `snapshot_id` | string | `YYYY-MM-DD`, or `YYYY-MM-DD-N` (N = 1, 2, …) for a further acquisition the same day; must equal the directory name |
| `acquired_at` | string | ISO-8601 acquisition timestamp with an explicit UTC designator (`Z` or `+00:00`) |
| `acquisition_url` | string | `http(s)` URL with a host and no credentials; the host is checked against the adapter's domain allowlist at admission |
| `acquisition_url_alt` | string, nullable | Alternate URL where a provider is mid-migration (dual-URL rule); same rules and allowlist check |
| `terms_archive` | string | File name of the archived terms page in force; must appear in `files` |
| `license_bucket` | `"A"` or `"B"` | Output bucket the source's derived content falls into ([ADR-0003](../roadmap/adr/0003-license-buckets-odbl.md)) |
| `license_note` | string | Human-readable license summary |
| `schema_version` | integer ≥ 1 | This dictionary's version at acquisition |
| `synthetic` | boolean | `true` only for wholly synthetic data (the tinycity fixture); `false` for real snapshots and for the committed CI samples cut from them (`phillysim/tests/fixtures/spine-samples/`) |
| `files` | object, non-empty | `{file name: SHA-256 hex digest}` for every file in the snapshot other than the manifest itself; names are bare file names (no path separators, drive letters, or `..`) |

`phillysim verify` checks each snapshot directory against its manifest: every
listed file present with the recorded digest, no unlisted file present,
directory names matching `source` / `snapshot_id`, and no stray entry in the
raw zone that no manifest vouches for.

## Quarantine reason file (`quarantine/<source>/<name>.reason.json`)

Written by `phillysim.quarantine` beside the snapshot directory it moved
(`quarantine/<source>/<name>/`, where `<name>` is the snapshot ID, suffixed
`-q2`, `-q3`, … if that ID was quarantined before). Nothing under
`quarantine/` is ever read by a pipeline stage.

| Field | Type | Meaning |
|---|---|---|
| `source`, `snapshot_id` | string | The snapshot as it was staged |
| `kind` | string | What refused it: a guard (`allowlist`, `size`, `zip_slip`, `bomb`), `manifest` (unparseable or malformed manifest), `verify` (checksum / layout mismatch), `terms` (the archived terms page no longer carries the wording the adapter expects: the acquisition stop condition, EP-5a), or `digest` (a delivered file's digest differs from the one the adapter pins or from the provider's checksum sidecar: the provider's bytes are not the pinned ones, EP-12) |
| `reason` | string | Human-readable detail naming the offending file, member, or URL; never an absolute path |
| `quarantined_at` | string | ISO-8601 UTC timestamp |
| `quarantined_as` | string | The directory name used under `quarantine/<source>/` |

## Stage state file (`<data root>/pipeline_state.json`)

Written by the stage runner (`phillysim.runner`, EP-4b) atomically after
every stage transition; read by `phillysim status` and `phillysim verify`.
Canonical JSON (two-space indent, sorted keys). It holds relative paths,
digests, parameters, and UTC timestamps only: never an absolute path or a
machine identifier. The runner's own `schema_version` (currently **1**) is
independent of this dictionary's.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | integer | State-file schema version (1) |
| `pipeline` | string | Name of the pipeline the file belongs to (`fixture` or `real`); a different pipeline's state is refused |
| `stages` | object | One record per stage that has ever started, keyed by stage name |

Each stage record:

| Field | Type | Meaning |
|---|---|---|
| `status` | `done`, `running`, `failed`, or `cancelled` | `done` only after every declared output was installed into its zone; anything else is *incomplete* and re-runs next time |
| `fingerprint` | string | SHA-256 of canonical JSON `{"inputs": {path: digest}, "params": {…}}`; the stage is skipped while this equals the current value and its outputs are intact |
| `inputs` | object | `{data-root-relative path: content digest}` at the time the stage started; a file's digest is its SHA-256, a directory's the SHA-256 of its sorted `path␀digest` listing |
| `params` | object | The stage's parameters as run (after any `--param` override) |
| `outputs` | object | `{data-root-relative path: content digest}` after installation; empty unless `done` |
| `started_at`, `finished_at` | string, nullable | ISO-8601 UTC timestamps |
| `error` | string, nullable | For `failed` / `cancelled`: exception type and message, with the data root replaced by `<data-root>` |

Stage outputs are staged under `cache/staging/<stage>/` and moved into their
zone by atomic rename; a leftover staging directory is a coherence problem
`verify` reports. The raw zone is immutable: a stage that re-produces an
existing snapshot must produce identical content or it fails.

## Curated tract spine (`curated/tracts_spine.parquet`, GeoParquet)

Written by the `spine` stage (real pipeline: `phillysim.spine`, EP-5b;
fixture pipeline: computed from tinycity). One row per 2020 census tract of
Philadelphia County, sorted by `geoid`; the real spine has **408** rows
(`phillysim.spine.TRACT_COUNT`, the stage's `expected_tracts` parameter and
its stop condition). Sources: geometry and name from TIGER/Line 2025,
population and the population-weighted center from CenPop2020, joined
one-to-one on GEOID (a tract without a center, or a center without a tract,
fails the stage: the two vintages must agree). The center is never recomputed
from the geometry. Data cards: [docs/data-cards/](data-cards/README.md).

| Column | Type | Meaning |
|---|---|---|
| `geoid` | string | Tract GEOID `42101######` (unique key) |
| `name` | string | Display name: TIGER `NAMELSAD` (`Census Tract 1.01`) |
| `population` | integer ≥ 0 | 2020 Census population from CenPop2020 (no sampling MOE); five real tracts have zero |
| `centroid_lon`, `centroid_lat` | float | Population-weighted center as published by CenPop2020, decimal degrees (NAD 83); the routing origin |
| `geometry` | Polygon / MultiPolygon | Tract boundary in the analysis CRS EPSG:26918 (ADR-0007); valid; within the county bounds |

The geospatial invariants (`phillysim.spine.check_spine`; roadmap/quality.md
test matrix) hold for every instance and are enforced by the stage itself:
CRS as declared; every geometry present, polygonal, valid, and inside the
county bounds (`adapters.base.COUNTY_BOUNDS` reprojected); every center
inside the county bounds; every `geoid` an eleven-digit Philadelphia County
2020 tract GEOID, unique, and the expected count; exactly one CenPop center
and (after `demographics`) one ACS row per tract, none unmatched.
`pytest --real-data-root DIR` runs them on a real data root.

## SNAP retailer layer (`snap_retailers.parquet`) — real pipeline, EP-6

One row per SNAP-authorized retailer in Philadelphia County as of the source
file's as-of date (`2025-12-31` for the pinned snapshot), written by the real
pipeline's `snap_retailers` stage (`phillysim.destinations`) from the
[`snap_retailers`](data-cards/snap-retailers.md) raw source and the spine.
GeoParquet, geometry in the analysis CRS, sorted by `site_id`. The rows with
`supermarket_format` true are the **supermarket-format** destination layer
(AM-4); the whole table is the **all-SNAP-retailer** variant M5 compares
with USDA's SRAM. Nothing is de-duplicated across sources (M4) and the file
carries no hours. The layer's invariants (`check_snap_layer`) are enforced
by the stage: CRS as declared, unique site IDs, classes from the published
mapping, points inside the county bounds, assigned tracts in the spine.

| Column | Type | Meaning |
|---|---|---|
| `site_id` | string | `snap_retailers:<Record ID>` (unique key; the sites table's key form) |
| `source` | string | `snap_retailers` |
| `source_record_id` | string | USDA's Record ID |
| `name` | string | Store name as published (untrusted text: escaped on output) |
| `store_type` | string | USDA's store type label, verbatim (one of the 17 in the mapping) |
| `format_class` | string | Project format class from the published mapping: `supermarket`, `grocery`, `combination`, `convenience`, `specialty`, `farmers_market`, or `other` ([method card](method-cards/store-formats.md)) |
| `supermarket_format` | boolean | `format_class == "supermarket"` (USDA `Supermarket` or `Super Store`) |
| `geoid` | string, nullable | Spine tract containing the point (point-in-polygon in the analysis CRS); null when no tract contains it (two rows in the pinned snapshot, named in the data card) |
| `longitude`, `latitude` | float | The provider's coordinates, as delivered (degrees) |
| `authorized_since` | timestamp | Start of the open authorization spell (the provider's Authorization Date) |
| `geometry` | Point, EPSG:26918 | The coordinates projected into the analysis CRS |

The stage also writes `intermediate/snap_retailers.json` (counts by store type
and format class, tracts covered, unassigned points, mapping version, as-of
date); the counts for the pinned snapshot are in the data card.

## Conflated sites (`sites.parquet`)

One row per destination after conflation, keyed by a source-scoped site ID.

| Column | Type | Meaning |
|---|---|---|
| `site_id` | string | `<source>:<source record id>` (unique key) |
| `source` | string | Source identifier |
| `source_record_id` | string | The source's own record ID |
| `category` | string | `supermarket_format`, `farmers_market`, or `meal_site` |
| `name` | string | Site name as published by the source (untrusted text: escaped on output) |
| `geoid` | string | Tract containing the point |
| `longitude`, `latitude` | float | Point location |
| `hours_status` | string | `parsed`, `missing`, `malformed`, or `not_in_source` |
| `open_weekday` | boolean, nullable | Open on at least one Monday–Friday; null unless `parsed` |
| `open_weekend` | boolean, nullable | Open on Saturday or Sunday; null unless `parsed` |
| `open_in_season_week` | boolean, nullable | Open on ≥1 day of the pinned in-season week (first full week of June) |
| `open_off_season_week` | boolean, nullable | Open on ≥1 day of the pinned off-season week (first full week of February) |

## Travel-time matrix (`travel_times.parquet`)

| Column | Type | Meaning |
|---|---|---|
| `origin_geoid` | string | Origin tract (population-weighted centroid) |
| `site_id` | string | Destination site |
| `mode` | string | `walk` or `walk_transit` |
| `time_median_min` | float | Typical time (median over departures), censored at 120 |
| `time_p85_min` | float | Time on slower departures (85th percentile), censored at 120 |

Key: (`origin_geoid`, `site_id`, `mode`). The fixture's matrix is a
deterministic stand-in (`fixture.json` → `travel_model`), not routing output.

## Analytic table (`tract_metrics.parquet`) — locked schema

One row per tract × metric (× category × mode where applicable). This is the
`{estimate, MOE, CV tier, reliability_action}` contract from
[methodology.md](../roadmap/methodology.md) "Uncertainty", enforced by
`phillysim.contracts.ANALYTIC_TABLE`.

| Column | Type | Meaning |
|---|---|---|
| `geoid` | string | Tract |
| `metric_id` | string | Metric identifier (`population_total`, `time_to_nearest_min`, …) |
| `category` | string, nullable | Destination category; null for tract-level quantities |
| `mode` | string, nullable | Travel mode; null where not applicable |
| `estimate` | float, nullable | The published value; null when the provider suppressed the input (never imputed, [ADR-0004](../roadmap/adr/0004-no-suppression.md)) |
| `moe` | float ≥ 0, nullable | 90 % margin of error; null for quantities without sampling error |
| `cv_tier` | integer 1–3, nullable | Coefficient-of-variation tier: 1 below 12 %, 2 from 12 % to below 40 %, 3 at or above 40 % (CV = (MOE / 1.645) / estimate); null when `moe` is null |
| `reliability_action` | `none` or `interval-only` | Display rule; `interval-only` when `cv_tier` is 3 (fixture assumption, confirmed or revised in M5) |
| `schema_version` | integer | This dictionary's version |
| `methods_version` | string | Methods / parameters version (any metric or pinned-parameter change bumps it) |

Class bins for map, table, and CSV are computed at build time from this table
and are not stored in it (the `publish` stage computes them; see "Public
zone" below).

**Instances.** The fixture's golden table (`population_total` with MOE and
CV tiers; `time_to_nearest_min` per category × mode). The real pipeline's
first instance (EP-7, `phillysim.metrics.slice`, `methods_version`
`slice-qa-1`) holds one row per tract of the **QA-only** metric
`qa_straight_line_m` (category `supermarket_format`, `mode` null): the
straight-line distance in metres, in the analysis CRS, from the tract's
population-weighted center to the nearest supermarket-format SNAP retailer;
`moe` and `cv_tier` null, `reliability_action` `none`
([method card](method-cards/qa-straight-line.md)). **A metric ID starting
with `qa_` is a quality-assurance column, never an access measure**
(methodology.md "Travel model"): the public manifest flags it `qa_only`, the
publish gate enforces the flag and the QA note, and the site may not present
it as access. M5 replaces the `metrics` stage body with the transparent
baseline family and keeps this column as QA.

## Intermediate files (undocumented by policy)

Files under `intermediate/` are working products between stages. Their shape
is owned by the stage that writes them, may change without a schema-version
bump, is never published, and is read by nothing outside the pipeline. They
are listed here so that every file the pipeline writes is accounted for (EP-9
checkpoint, 2026-09-02); their columns are deliberately not documented.

| File | Written by | Read by | Contents |
|---|---|---|---|
| `intermediate/acquisition.json` | `acquire` (real pipeline, EP-5a) | nobody (report) | Per-source acquisition report: the per-source snapshot IDs (`snapshot_ids`, EP-12), and per source its snapshot ID, acquisition URL, whether an existing verified snapshot was re-used, each fetch's URL / bytes / attempts / seconds, the pinned digests and provider sidecars checked (`digests_checked`, EP-12), the filter placement note, and the guard limits applied |
| `intermediate/validation.json` | `validate` | nobody (report) | Per-source contract report: snapshot ID, license bucket, schema version, row count, null counts per contract column (real pipeline), violations |
| `intermediate/acs_tracts.parquet` | `demographics` | `metrics` | ACS estimate / MOE columns (`<table>_<line>E` / `…M`) per spine tract; real pipeline (EP-5b): `geoid` + the pinned `B01003_001E/M`, `B08201_002E/M` as float64, exactly one row per spine tract in spine order, suppressed cells null (ADR-0004), join cardinality enforced |
| `intermediate/snap_retailers.json` | `snap_retailers` (real pipeline, EP-6) | nobody (report) | Counts for the SNAP retailer layer: rows, supermarket-format rows, by store type, by format class, tracts with any / with a supermarket-format retailer, points unassigned to a tract, mapping version, as-of date, CRS |
| `intermediate/basemap.json` | `basemap` (real pipeline, EP-8b) | nobody (report) | Counts for the basemap roads layer: rows, by MTFCC class, by route type, unnamed roads, total length in km, length outside the spine's tracts in metres (0.0 for the pinned snapshot), CRS |
| `intermediate/slice_metric.json` | `metrics` (real pipeline, EP-7) | nobody (report) | The QA slice metric's report: metric ID, category, methods version, tract and destination counts, null estimates, min / median / max distance in metres |
| `intermediate/destinations.parquet` | `destinations` | `conflate` | The destination sources as one point table (site ID, source, category, name, tract, coordinates) |
| `intermediate/sites_conflated.parquet` | `conflate` | `hours` | Destinations after cross-source de-duplication (identity on the fixture) |
| `intermediate/network.json` | `network` | `travel_times` (fixture); nobody yet in the real pipeline (EP-13's harness reads `intermediate/network/`) | Routing-input summary. Fixture: stop count, edge count, total edge length, CRS. Real pipeline (EP-12): the routing box (county bounds + `buffer_m`, WGS 84), CRS, the two source snapshots, the license bucket by derivation (B), the clip's file name, bytes, node / way / highway-way / relation counts and the state file's counts, and per feed zip its bytes, stops, stops outside the box, and stops inside the county's tracts |
| `intermediate/network/` | `network` (real pipeline, EP-12) | the routing harness (EP-13; nothing in the pipeline yet) | A directory output (like `public/`): `pennsylvania-260831-philadelphia-5km.osm.pbf`, the OSM extract clipped to the routing box (way-complete, the source order, the box in its header; **Bucket B** by derivation from the `osm_network` snapshot), and `google_bus.zip` / `google_rail.zip`, SEPTA's two feed zips copied out of the release asset as files and never expanded (never copied under `public/` or `site/`) |

## Public zone (`public/`) — public schema version 2 (EP-7, EP-8b)

Written as a whole by the `publish` stage of either pipeline
(`phillysim.publish.export`; the zone directory is the stage's single
output, so the runner installs or replaces it atomically and a gate failure
leaves nothing behind). Everything here is WGS 84, license-labeled per file,
escaped, and checked by the publish gate (`phillysim.publish.gate`;
`phillysim gate`) before it is installed and again in CI. The **public schema
version** (`public_schema_version`, currently **2**) is a parameter of the
`publish` stage and a member of every public file; any change to the files,
columns, or manifest shape below bumps it, with a note here, and the gate
refuses a zone whose version is not the one it checks (so a stale zone is
rebuilt, never read). **Version history:** 1 (EP-7) the four tract and site
files; 2 (EP-8b) adds `basemap.geojson`, the manifest's `basemap` member,
and the `basemap` column list; no earlier file or column changed. No file
under any `public/` zone is tracked in the repository; the site (EP-8a, M6)
reads these files and nothing else: `phillysim site build` re-runs the
gate, copies the six files verbatim into `site/dist/data/`, and adds
`site.json` with every digest (nothing is derived at build time since
version 2). `site/dist/` is a build output, not a zone, and is gitignored.

| File | Contents |
|---|---|
| `manifest.json` | The label registry (below) |
| `tracts.geojson` | FeatureCollection, one feature per spine tract, feature `id` = `geoid`, polygon geometry, properties = the tracts columns |
| `tracts.csv` | The same rows and columns without geometry (the table-parity source) |
| `sites.geojson` | FeatureCollection, one feature per published facility point, feature `id` = `site_id`, point geometry, properties = the sites columns minus coordinates |
| `sites.csv` | The same rows with `longitude` / `latitude` columns |
| `basemap.geojson` | FeatureCollection, the minimal public-domain basemap (ADR-0005), feature `id` = `feature_id`, one `layer` per feature: the `county_boundary` (one polygon feature, the spine's tract polygons dissolved) and the `roads` (one line feature per curated major road; absent from a pipeline without a roads source, as the fixture is). Since version 2 |

**Basemap columns.** `feature_id` (`county_boundary` for the boundary,
`roads:<linearid>` for a road), `layer` (`county_boundary` or `roads`),
`name` (the boundary's name, `Philadelphia County` for the real pipeline;
the road's TIGER `FULLNAME`, nullable), and for roads `linearid`, `mtfcc`
(`S1100` primary, `S1200` secondary), `route_type` (TIGER `RTTYP`: `I`
interstate, `U` US, `S` state, `C` county, `M` common name, `O` other); the
boundary carries the road columns as nulls so every feature has the same
properties. The boundary is drawn first, the roads follow sorted by
identifier. The basemap has no CSV twin (nothing tabular to compare) and no
`fields` entry (it carries no metric).

**Tracts columns.** `geoid`, `name`, `population` (the spine's 2020 Census
count, no MOE), then, for every tract-metric the analytic table holds, a
group of five columns named from the metric's key,
`<metric_id>[__<category>][__<mode>]` (parts joined by two underscores; null
parts omitted; `qa_straight_line_m__supermarket_format`,
`time_to_nearest_min__farmers_market__walk`): the estimate under the bare
column name, `_moe`, `_cv_tier`, `_reliability_action` (the analytic
table's four values, so map, table, and CSV carry the same
{estimate, MOE, CV tier, action}), and `_bin`, the build-time class.
Columns are lowercase slugs and carry none of the terms the claims matrix
prohibits (the gate rejects `score`, `rank`, `index`, `desert`, `healthy`,
…); a metric whose ID starts with `qa_` is QA-only (above).

**Sites columns.** `site_id`, `source`, `category`, `name` (the provider's
text, untrusted: escaped in CSV, a plain string in GeoJSON), `geoid`
(nullable: the tract containing the point), and in the CSV `longitude`,
`latitude` (WGS 84, six decimals). The real pipeline publishes the
supermarket-format SNAP retailers the slice metric was computed against; the
fixture publishes its conflated sites table.

**Bins.** For every metric column the stage computes class edges over the
column's non-null values (quantiles, five classes requested; ties collapse
edges, so a column may get fewer classes, never zero when a value exists)
and writes each row's 1-based class in `<column>_bin` (null where the
estimate is null). The edges are recorded in the manifest under `bins`
(`method`, `classes_requested`, `classes`, `edges`); the site never bins on
its own ([methodology.md](../roadmap/methodology.md) "Uncertainty":
build-time bins so map, table, and CSV agree).

**License labels (ADR-0003).** Every file's bucket is *derived* from the
buckets of the sources it is built from (`manifest.json` in each raw
snapshot): Bucket B if any source is Bucket B, else A. The label
(`bucket`, `spdx_id`, `name`, `url`, `notices`) is written into the
manifest per file and, for GeoJSON, in-file as the top-level `license`
member beside `attribution` (RFC 7946 foreign members); CSV has no slot for
it, so the manifest is its sidecar. Bucket B labels carry the ODbL notice
and "© OpenStreetMap contributors". The gate refuses a file whose label
differs from the derived bucket or whose in-file label differs from the
manifest's ([docs/DATA-LICENSES.md](DATA-LICENSES.md)).

**Escaping and determinism.** String cells in CSV that start with `=`, `+`,
`-`, `@`, tab, or carriage return are prefixed with `'` (spreadsheet
formula injection; the gate rejects an unescaped cell, allowing a leading
`-` only on a plain number). GeoJSON is written with sorted keys, compact
separators, UTF-8, polygon rings oriented per RFC 7946, and `\n` line ends;
CSV with `\n` line ends; so a rebuilt zone is byte-identical.

**`manifest.json`.** Canonical JSON (sorted keys). Members:

| Member | Meaning |
|---|---|
| `pipeline` | `fixture` or `real` |
| `schema_version`, `public_schema_version`, `methods_version` | The dictionary's schema version and the methods version carried by the analytic table; the public schema version (this section) |
| `license`, `attribution` | The zone-wide label (every file shares the sources) and the sources' citations, de-duplicated |
| `crs`, `bounds`, `coordinate_decimals` | `EPSG:4326`; `[minx, miny, maxx, maxy]` in degrees every published coordinate must lie in (the stage's `bounds` parameter: the county bounds for the real pipeline, the grid for the fixture); the rounding applied |
| `sources` | One record per source the zone derives from: `source`, `snapshot_id`, `license_bucket`, `license_note`, `synthetic`, `citation` (never a path) |
| `fields` | One record per published metric column: `column`, `metric_id`, `category`, `mode`, `qa_only`, `description` |
| `bins` | Per metric column: the edge record above |
| `columns` | The ordered column lists of `tracts` and `sites` (the CSV headers) and, since version 2, `basemap` (the basemap properties) |
| `basemap` | Since version 2: `file` (`basemap.geojson`) and `layers`, the feature count per layer present (`county_boundary` always 1; `roads` when the pipeline has a roads source) |
| `files` | Per file: `table` (`tracts`, `sites`, or `basemap`), `format`, `rows`, `bucket`, `license`, `attribution`, `sources`, `sha256`, `bytes` |
| `qa_note` | Present when any field is `qa_only`: the sentence that QA columns are not access measures |

The gate (`phillysim.publish.gate.check_public_zone`) checks, in order: the
manifest parses and every file in the directory is listed with a matching
digest and size (nothing unlisted, nothing missing, no subdirectories);
every file's bucket equals the bucket derived from its sources, its label is
that bucket's, Bucket B files carry the notices, attribution covers every
source, and GeoJSON in-file labels agree; GeoJSON is a FeatureCollection
without a `crs` member whose every position is a valid longitude / latitude
inside the declared bounds (which must equal the pipeline's when the caller
supplies them); no CSV cell starts with a formula character; no file
(manifest included) mentions a pipeline zone path, the state file, or an
absolute path; names are slugs without prohibited terms and `qa_` columns
are declared; both formats of a table hold the same keys and row count,
with the CSV header equal to the manifest's column list; and, since version
2, the manifest declares this gate's public schema version and a `basemap`
member naming a listed file of table `basemap` whose features all sit in a
declared layer with the declared counts, exactly one polygon county
boundary among them, lines for the roads, and the basemap columns as every
feature's properties.

## Basemap roads layer (`curated/basemap_roads.parquet`, GeoParquet) — real pipeline, EP-8b

Written by the `basemap` stage (`phillysim.basemap`). One row per primary or
secondary road of Philadelphia County from the TIGER/Line 2025 county roads
file (MTFCC `S1100` / `S1200`; the local streets in the same file are
dropped at the adapter's read), sorted by `linearid`; the pinned snapshot
has **426** rows, 1,044 km. The geometry is the provider's, reprojected and
nothing else: no clipping, no simplification. The county boundary the
basemap also draws is not a layer here (the `publish` stage dissolves the
spine's polygons). Data card:
[docs/data-cards/tiger-roads.md](data-cards/tiger-roads.md).

| Column | Type | Meaning |
|---|---|---|
| `linearid` | string | TIGER `LINEARID` (unique key) |
| `name` | string, nullable | TIGER `FULLNAME` (every road of the pinned snapshot has one) |
| `mtfcc` | string | `S1100` (primary road) or `S1200` (secondary road) |
| `route_type` | string | TIGER `RTTYP`: `I`, `U`, `S`, `C`, `M`, `O` |
| `geometry` | LineString / MultiLineString | The road centerline in the analysis CRS EPSG:26918 (ADR-0007); valid; within the county bounds |

The layer's invariants (`phillysim.basemap.check_roads`), enforced by the
stage on its own output: CRS as declared; `linearid` present and unique;
`mtfcc` and `route_type` within their vocabularies; every geometry present,
a line, valid, and inside the county bounds; every road intersecting the
union of the spine's tracts (the county scope the provider's file promises;
the stage report records the length outside it, 0.0 m for the pinned
snapshot). `pytest --real-data-root DIR` runs them on a real data root.

## Raw sources: the tract spine (EP-5a), SNAP retailers (EP-6), the basemap roads (EP-8b), and the routing sources (EP-12)

Real snapshots are stored **as delivered** by the provider (byte-for-byte,
so `phillysim verify` and anyone else can check them against the source) and
the Philadelphia County filter is applied when the adapter reads them; the
tables below describe what the adapter's `read` returns, which is what the
`validate` stage checks against the contract
(`phillysim/src/phillysim/adapters/`). Coordinates in the Census tables are
NAD 83 (EPSG:4269) as delivered; the `spine` stage reprojects into the
analysis CRS (EPSG:26918, [ADR-0007](../roadmap/adr/0007-analysis-crs.md)).
Every Census snapshot directory also holds `terms.html`, the archived Census
Bureau Open Government page (the terms in force), and a manifest with
`license_bucket = "A"`. Snapshot IDs are **per source**
(`phillysim.pipeline.SNAPSHOT_IDS`, EP-12): the five sources below acquired
on 2026-09-02 keep that ID and the two routing sources carry 2026-09-03.
The routing sources are not tables: their `read` returns the summary the
`validate` stage checks, and the `network` stage reads them a second way
(the clip, the unwrap) into `intermediate/network/`.

### `raw/osm_network/<snapshot-id>/` — OpenStreetMap extract for Pennsylvania via Geofabrik (EP-12)

File `pennsylvania-260831.osm.pbf`, Geofabrik's dated state extract (OSM
data of 2026-08-31; 345,912,530 bytes; never the `-latest` file), stored as
delivered beside the provider's MD5 sidecar `pennsylvania-260831.osm.pbf.md5`
(fetched through the same guarded path; the adapter pins the same MD5) and
`terms.html`, the Geofabrik region page in force, checked in its visible
text for "created by OpenStreetMap Contributors" and "License: ODbL". The
manifest carries **`license_bucket = "B"`**, the first of the real
pipeline (ADR-0003). A PBF is not an archive: the download path caps it at
1 GiB and never opens it as a zip. `read` opens the file's **header only**
and returns one row ([data card](data-cards/osm-network.md)):

| Column | Type | Meaning |
|---|---|---|
| `file` | string | `pennsylvania-260831.osm.pbf` (key) |
| `bytes` | integer | The delivered file's size, within the 1 GiB cap |
| `md5`, `md5_pinned`, `md5_sidecar` | string | The file's MD5, the one the adapter pins (ADR-0008), and the one the provider's sidecar states |
| `sidecar_match` | integer | 1 when `md5` equals `md5_sidecar` (required) |
| `generator`, `replication_timestamp`, `sorting` | string | The header's writing program, OSM data timestamp (`YYYY-MM-DDThh:mm:ssZ`), and sort order (`Type_then_ID` required) |
| `bbox_min_lon`, `bbox_min_lat`, `bbox_max_lon`, `bbox_max_lat` | float | The header's bounding box, which must enclose the county bounds (the right region, whole) |

The county filter is the **clip** (`phillysim.adapters.osm.clip`, run by
the `network` stage): the county bounds buffered by 5 km in the analysis
CRS, expressed in WGS 84; every way with a node inside the box with all of
its nodes, restriction relations whose members are all kept, the source
order, the box in the header. Its own contract (`osm.check_clip`) is
enforced by the stage on its output: a readable PBF whose header carries
the box, node and way counts within the recorded bands (the stage's
`node_band` / `way_band` parameters), every node inside the box or
referenced by a kept way, `highway` ways present.

### `raw/gtfs/<snapshot-id>/` — SEPTA GTFS, release v202609060 (EP-12)

File `gtfs_public.zip`, SEPTA's release asset as SEPTA publishes it on
GitHub (21,555,258 bytes; SHA-256 pinned in the adapter and checked at
acquisition), holding `google_bus.zip` and `google_rail.zip`, stored as
delivered, plus `terms.html`, SEPTA's developer page (the license
agreement in force), checked for its two "SEPTA reserves the right …"
sentences; the manifest carries `license_bucket = "A"` and a `license_note`
stating the terms and the project's facts-not-contents position. No county
filter (stops outside the routing box are counted, not dropped). `read`
inspects each inner zip in place through the nested guards and returns one
row per feed ([data card](data-cards/septa-gtfs.md)):

| Column | Type | Meaning |
|---|---|---|
| `feed` | string | `google_bus.zip` or `google_rail.zip` (key; exactly the two) |
| `label` | string | `bus_metro` or `rail` |
| `bytes`, `members` | integer | The inner zip's stored size (within the 128 MiB cap) and member count |
| `missing_required`, `missing_names` | integer; string, nullable | Required GTFS files and columns absent (must be 0) and their names |
| `feed_publisher`, `feed_version` | string | From `feed_info.txt`: `SEPTA`; the release tag `v202609060` |
| `feed_start_date`, `feed_end_date` | string | The feed's authoritative window, `YYYYMMDD` |
| `covers_wednesday`, `covers_saturday` | integer | 1 when the pinned Wednesday (2026-09-23) / Saturday (2026-09-26) lies inside the window (required) |
| `services_wednesday`, `services_saturday` | integer ≥ 1 | Service IDs running on each pinned day per `calendar.txt` and `calendar_dates.txt` |
| `agency_timezone` | string | `America/New_York` (required) |
| `stops`, `stops_outside_box` | integer | Stops in the feed and how many lie outside the routing box (information, not a failure) |
| `routes`, `trips` | integer ≥ 1 | Row counts of `routes.txt` and `trips.txt` |

The `network` stage **unwraps without expanding**
(`phillysim.adapters.septa_gtfs.unwrap`): the outer archive inspected, each
inner zip inspected in place and again as a file, the two feed zips copied
out into `intermediate/network/`; nothing inside a feed is ever extracted,
and nothing from the feed ever reaches `public/` or `site/`.

### `raw/snap_retailers/<snapshot-id>/` — USDA SNAP Retailer Locator historical data (EP-6)

`snap-retailer-locator-data2005-2025.zip` as delivered (one CSV member, read
in place) plus `source-page.html`, the provider's data page in force
(archived in lieu of a terms page; see the [data card](data-cards/snap-retailers.md)),
and the manifest (`license_bucket = "A"`, dual URLs for the FNS→FNA
rename). `read` returns the provider's fifteen columns verbatim as strings
(whitespace stripped, blank cells null; `Latitude` / `Longitude` as float),
filtered to `State = "PA"`, `County = "PHILADELPHIA"`, and open
authorization spells (`End Date` null), sorted by numeric `Record ID`, with
WGS 84 point geometry. Contract: `Record ID` unique and numeric; `Store
Type` within the mapped vocabulary (a new label fails validation: the stop
condition); `State`, `County` fixed; `Zip Code` five digits; `Authorization
Date` `M/D/YYYY`; points inside the county bounds. 1,609 rows for the pinned
snapshot.

### `raw/tiger_tracts/<snapshot-id>/` — TIGER/Line 2025 census tracts

File `tl_2025_42_tract.zip`, the Census Bureau's Pennsylvania tract layer
(2020-vintage tracts as of 2025-01-01), read straight from the zip through
pyogrio and filtered to `STATEFP = 42`, `COUNTYFP = 101`. Every TIGER
attribute is kept; the contract requires:

| Column | Type | Meaning |
|---|---|---|
| `GEOID` | string | Eleven-digit 2020 tract GEOID `42101######` (unique key) |
| `STATEFP`, `COUNTYFP`, `TRACTCE` | string | FIPS components (`42`, `101`, six digits) |
| `NAME`, `NAMELSAD` | string | Tract number and its legal/statistical description (`Census Tract 1.01`) |
| `ALAND`, `AWATER` | integer ≥ 0 | Land and water area, square metres |
| `geometry` | Polygon / MultiPolygon | Tract boundary, valid, within the county bounds, EPSG:4269 |

### `raw/tiger_roads/<snapshot-id>/` — TIGER/Line 2025 county roads (EP-8b)

File `tl_2025_42101_roads.zip`, the Census Bureau's roads layer for
Philadelphia County (the Bureau distributes roads per county, so the file
is county-scoped as delivered), read straight from the zip through pyogrio
and filtered to the primary and secondary feature classes; the local
streets, ramps, service drives, alleys, and walkways in the same file never
leave the raw zone. Every TIGER attribute is kept; the contract requires:

| Column | Type | Meaning |
|---|---|---|
| `LINEARID` | string | TIGER linear feature identifier, 10 to 16 digits (unique key) |
| `FULLNAME` | string, nullable | The road's full name as the Bureau records it |
| `RTTYP` | string | Route type: `C`, `I`, `M`, `O`, `S`, or `U` |
| `MTFCC` | string | Feature class, `S1100` (primary) or `S1200` (secondary) after the filter |
| `geometry` | LineString / MultiLineString | Road centerline, valid, within the county bounds, EPSG:4269 |

### `raw/cenpop/<snapshot-id>/` — CenPop2020 tract centers of population

File `CenPop2020_Mean_TR42.txt`, the Census Bureau's 2020 mean centers of
population for Pennsylvania's tracts (comma-separated, UTF-8 with a byte-order
mark), filtered to Philadelphia County. The adapter derives `geoid` and the
point geometry; these centroids are the routing origins and are never
recomputed from tract geometry.

| Column | Type | Meaning |
|---|---|---|
| `geoid` | string | `STATEFP + COUNTYFP + TRACTCE` (unique key) |
| `STATEFP`, `COUNTYFP`, `TRACTCE` | string | FIPS components as delivered |
| `POPULATION` | integer ≥ 0 | 2020 Census population (no sampling MOE) |
| `LATITUDE`, `LONGITUDE` | float | Population-weighted center, decimal degrees |
| `geometry` | Point | The center, EPSG:4269, within the county bounds |

### `raw/acs/<snapshot-id>/` — ACS 5-year 2020–2024 selected tables

Files `acsdt5y2024-b01003.dat` and `acsdt5y2024-b08201.dat` from the Census
Bureau's table-based summary file (pipe-delimited, one row per geography at
every summary level, `<TABLE>_E<line>` / `<TABLE>_M<line>` columns). The
adapter keeps the county's tract rows (`GEO_ID` prefix `1400000US42101`),
selects the pinned variables, renames them to the `<table>_<line>E` / `…M`
form used throughout this dictionary, and turns the provider's annotation
values (`-999999999`, `-888888888`, `-666666666`, `-555555555`, `-333333333`,
`-222222222`) and blank cells into nulls ([ADR-0004](../roadmap/adr/0004-no-suppression.md):
suppressed stays missing). The pinned variable list is the one methodology.md
and the `demographics` stage name; adding a variable is a methods-version bump
([ADR-0006](../roadmap/adr/0006-versioning-axes.md)).

| Column | Type | Meaning |
|---|---|---|
| `geoid` | string | Last eleven characters of `GEO_ID` (unique key) |
| `B01003_001E`, `B01003_001M` | float ≥ 0, nullable | Total population estimate and 90 % margin of error |
| `B08201_002E`, `B08201_002M` | float ≥ 0, nullable | Households with no vehicle available, estimate and 90 % MOE |

## Raw fake sources (fixture only)

Column-level contracts for the eight tinycity sources live in
`phillysim/src/phillysim/fixtures/tinycity_contracts.py`; they mirror the
shape of the real sources loosely (SNAP-like retailers with a format-based
`store_type`; markets with free-text `hours` / `months`; meal sites with
`<day>_open` / `<day>_close` in `HH:MM`; ACS columns as `<table>_<line>E` /
`…M`). The three spine sources, the SNAP retailer source (EP-6), the roads
source (EP-8b), and the two routing sources (EP-12: `osm_network` and
`gtfs`, whose fixture counterparts stay stubs by decision, ADR-0008) have
real contracts (above); the remaining destination sources keep their
fixture contracts until their adapters land (M4).
