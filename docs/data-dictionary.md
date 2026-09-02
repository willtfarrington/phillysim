# Data dictionary

> **Status: seeded (EP-3).** Schema version **1**. This document describes the
> tables the pipeline produces; today the only instances are the synthetic
> tinycity fixture's golden files (`phillysim/tests/fixtures/tinycity/`). The
> integer schema version is one of the manifest-recorded version axes
> ([ADR-0006](../roadmap/adr/0006-versioning-axes.md)): any breaking change to
> a table shape below bumps it, with a migration note here. Column names are
> format-based and carry no nutrition-quality adjectives
> ([docs/CLAIMS.md](CLAIMS.md)).

Conventions: `geoid` is the eleven-digit 2020 census-tract GEOID (state +
county + tract). Coordinates are WGS 84 (EPSG:4326) at every boundary shown
here; the analysis CRS is chosen in EP-5b and will be recorded in this file.
Times are minutes. Nullable columns say so; everything else is required.

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
| `synthetic` | boolean | `true` only for fixtures |
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
| `kind` | string | What refused it: a guard (`allowlist`, `size`, `zip_slip`, `bomb`), `manifest` (unparseable or malformed manifest), or `verify` (checksum / layout mismatch) |
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

## Curated tract spine (`tracts_spine.parquet`, GeoParquet)

| Column | Type | Meaning |
|---|---|---|
| `geoid` | string | Tract GEOID (unique key) |
| `name` | string | Display name |
| `population` | integer | Decennial population (no sampling MOE) |
| `centroid_lon`, `centroid_lat` | float | Population-weighted centroid (the routing origin) |
| `geometry` | Polygon / MultiPolygon | Tract boundary |

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
| `intermediate/validation.json` | `validate` | nobody (report) | Per-source contract report: snapshot ID, license bucket, schema version, row count, violations |
| `intermediate/acs_tracts.parquet` | `demographics` | `metrics` | ACS estimate / MOE columns (`<table>_<line>E` / `…M`) per spine tract |
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

## Raw fake sources (fixture only)

Column-level contracts for the eight tinycity sources live in
`phillysim/src/phillysim/fixtures/tinycity_contracts.py`; they mirror the
shape of the real sources loosely (SNAP-like retailers with a format-based
`store_type`; markets with free-text `hours` / `months`; meal sites with
`<day>_open` / `<day>_close` in `HH:MM`; ACS columns as `<table>_<line>E` /
`…M`) and are replaced by each real adapter's contract from EP-5 on.
