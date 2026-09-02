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
here; the analysis CRS is chosen in EP-5 and will be recorded in this file.
Times are minutes. Nullable columns say so; everything else is required.

## Snapshot manifest (`raw/<source>/<snapshot-id>/manifest.json`)

Proposed shape, owned by the manifest engine from EP-4a.

| Field | Type | Meaning |
|---|---|---|
| `source` | string | Source identifier (matches the directory name) |
| `snapshot_id` | string | Date-stamped per-source snapshot identifier |
| `acquired_at` | string | ISO-8601 UTC acquisition timestamp |
| `acquisition_url` | string | URL the snapshot was fetched from |
| `acquisition_url_alt` | string, nullable | Alternate URL where a provider is mid-migration (dual-URL rule) |
| `terms_archive` | string | File name of the archived terms page in force |
| `license_bucket` | `"A"` or `"B"` | Output bucket the source's derived content falls into ([ADR-0003](../roadmap/adr/0003-license-buckets-odbl.md)) |
| `license_note` | string | Human-readable license summary |
| `schema_version` | integer | This dictionary's version at acquisition |
| `synthetic` | boolean | `true` only for fixtures |
| `files` | object | `{file name: SHA-256 hex digest}` for every file in the snapshot |

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

## Raw fake sources (fixture only)

Column-level contracts for the eight tinycity sources live in
`phillysim/src/phillysim/fixtures/tinycity_contracts.py`; they mirror the
shape of the real sources loosely (SNAP-like retailers with a format-based
`store_type`; markets with free-text `hours` / `months`; meal sites with
`<day>_open` / `<day>_close` in `HH:MM`; ACS columns as `<table>_<line>E` /
`…M`) and are replaced by each real adapter's contract from EP-5 on.
