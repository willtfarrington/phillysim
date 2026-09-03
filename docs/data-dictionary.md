# Data dictionary

> **Status: seeded (EP-3); first real instances (EP-5b).** Schema version
> **1**. This document describes the tables the pipeline produces. Instances
> today: the synthetic tinycity fixture's golden files
> (`phillysim/tests/fixtures/tinycity/`) for every table, and, since EP-5b,
> the real curated tract spine and its ACS join in the gitignored data root.
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
| Curated tract spine `geometry`; every analysis-zone geometry derived from it (sites, travel-time inputs, metrics, from EP-6 on) | EPSG:26918 | the analysis CRS; recorded in each GeoParquet file's metadata |
| `centroid_lon` / `centroid_lat` in the spine; `longitude` / `latitude` in the sites table | degrees (NAD 83 as published; treated as WGS 84 at publication, ADR-0007 datum note) | the form routing origins and destinations take; `phillysim.spine.centroids_in` projects the spine's centers on demand |
| Public zone (`public/`, GeoJSON / CSV) | WGS 84, EPSG:4326 | the publication boundary, and nowhere else |
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
| `kind` | string | What refused it: a guard (`allowlist`, `size`, `zip_slip`, `bomb`), `manifest` (unparseable or malformed manifest), `verify` (checksum / layout mismatch), or `terms` (the archived terms page no longer carries the wording the adapter expects: the acquisition stop condition, EP-5a) |
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
| `pipeline` | string | Name of the pipeline the file belongs to (`fixture` today); a different pipeline's state is refused |
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
and are not stored in it.

## Intermediate files (undocumented by policy)

Files under `intermediate/` are working products between stages. Their shape
is owned by the stage that writes them, may change without a schema-version
bump, is never published, and is read by nothing outside the pipeline. They
are listed here so that every file the pipeline writes is accounted for (EP-9
checkpoint, 2026-09-02); their columns are deliberately not documented.

| File | Written by | Read by | Contents |
|---|---|---|---|
| `intermediate/acquisition.json` | `acquire` (real pipeline, EP-5a) | nobody (report) | Per-source acquisition report: snapshot ID, acquisition URL, whether an existing verified snapshot was re-used, each fetch's URL / bytes / attempts / seconds, the filter placement note, and the guard limits applied |
| `intermediate/validation.json` | `validate` | nobody (report) | Per-source contract report: snapshot ID, license bucket, schema version, row count, null counts per contract column (real pipeline), violations |
| `intermediate/acs_tracts.parquet` | `demographics` | `metrics` | ACS estimate / MOE columns (`<table>_<line>E` / `…M`) per spine tract; real pipeline (EP-5b): `geoid` + the pinned `B01003_001E/M`, `B08201_002E/M` as float64, exactly one row per spine tract in spine order, suppressed cells null (ADR-0004), join cardinality enforced |
| `intermediate/destinations.parquet` | `destinations` | `conflate` | The destination sources as one point table (site ID, source, category, name, tract, coordinates) |
| `intermediate/sites_conflated.parquet` | `conflate` | `hours` | Destinations after cross-source de-duplication (identity on the fixture) |
| `intermediate/network.json` | `network` | `travel_times` | Routing-input summary: stop count, edge count, total edge length, CRS |

## Placeholder public export (`public/tract_metrics.csv`)

Written by the `publish` stage of the fixture pipeline (EP-4b): the analytic
table above as plain CSV, one row per record, same columns. It carries **no
license label and no CSV formula-injection escaping**, exists only in the
gitignored fixture data root, and is not a published output; the publish
gate in EP-7 replaces it with per-file license-bucket labels and escaping
([docs/DATA-LICENSES.md](DATA-LICENSES.md)). No file under any `public/`
zone is tracked in the repository.

## Raw sources: the tract spine (EP-5a)

Real snapshots are stored **as delivered** by the provider (byte-for-byte,
so `phillysim verify` and anyone else can check them against the source) and
the Philadelphia County filter is applied when the adapter reads them; the
tables below describe what the adapter's `read` returns, which is what the
`validate` stage checks against the contract
(`phillysim/src/phillysim/adapters/`). Coordinates in these tables are NAD 83
(EPSG:4269) as delivered; the `spine` stage reprojects into the analysis CRS
(EPSG:26918, [ADR-0007](../roadmap/adr/0007-analysis-crs.md)). Every snapshot
directory also holds `terms.html`, the archived Census Bureau Open Government
page (the terms in force), and a manifest with `license_bucket = "A"`.

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
`…M`). The three spine sources now have real contracts (above); the five
destination, transit, and network sources keep their fixture contracts until
their adapters land (EP-6, M3, M4).
