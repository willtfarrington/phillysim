# Data licenses

> **Status: stub (pre-acquisition).** No source data has been acquired or
> published yet. This document states the licensing rules the project has
> adopted and will be expanded with per-snapshot terms records as each source
> is actually ingested. It mirrors the source matrix in
> [roadmap/sources.md](../roadmap/sources.md); that matrix is the working
> record, this file is the shipped statement.

## The OpenDataPhilly umbrella

The OpenDataPhilly catalog licenses nothing; each originator's terms govern
acquisition, derivatives, and redistribution. Every source below is assessed
against its **originator's** terms, not the catalog listing.

## City of Philadelphia license position (confirmed in writing, 2026-09-02)

The operative City of Philadelphia license text **reserves all rights and
contains no express grant**. This project's reuse of City datasets (farmers'
markets, free food & meal sites, planning districts) relies on the open-data
publication context: the datasets' "Public Use; Free" record markings and the
Open Data Program's stated purpose.

That reading was put to the City in writing and **confirmed on 2026-09-02**
by the GIS Manager of CityGeo (Office of Innovation & Technology), the office
that runs the Open Data Program: the City has no terms beyond the published
open-data terms page, and shares the data "for people to use in any way they
want to benefit the community." The formal license text itself is unchanged,
so the standing safeguards remain:

- The written reply is kept with the project's records and will be archived
  beside the terms page in force with the first City snapshot; the terms
  pages in force are archived alongside every snapshot.
- The project maintains takedown readiness: if the City objects, affected
  layers are removed and the change is recorded in the changelog.

## License buckets for published outputs (ADR-0003)

Every file the project publishes (in `data/public/` and in the site's data
payloads) carries a per-file license label in one of two buckets:

- **Bucket A — CC BY 4.0:** prose, method/data cards, and derived tables
  containing no OSM-derived contents.
- **Bucket B — ODbL:** any table containing OSM-derived contents (travel-time
  matrices, metric columns computed over the OSM network) — including
  **every combined export** (table CSVs, the site's GeoJSON payloads), by
  rule. In-file/sidecar attribution: ODbL + "© OpenStreetMap contributors."
  Rendered maps are Produced Works (attribution notice only).

Public-domain inputs impose nothing; carrying ACS columns inside an ODbL file
creates no conflict. CI validates per-file license labels at the publish
gate.

**Labeling status (EP-9 checkpoint, 2026-09-02).** Nothing has been
published. The only `public/` file that exists today is the fixture
pipeline's placeholder export, `public/tract_metrics.csv` under the
gitignored fixture data root: it is **unlabeled** (no bucket label, no
attribution notice, no CSV escaping) until EP-7 builds the publish gate, and
it is not a published output. No file under any `public/` zone is tracked in
the repository. The eight synthetic tinycity manifests do carry bucket
labels (seven Bucket A; `osm_network` Bucket B, as OSM-shaped content), and
each source's contract pins its bucket: the contract suite checks them on
every test run and the `validate` stage on every `phillysim run --fixture`.

**SEPTA-derived aggregates:** computed travel times are facts; published
matrices contain no GTFS feed contents. The raw feed is never republished,
and SEPTA's terms are re-read and archived at every refresh.

## Source terms summary (to be expanded per snapshot)

| Source | License/terms | Status |
|---|---|---|
| USDA SNAP retailer file | US public domain | committed |
| City Farmers' Markets (ODP/ArcGIS) | City terms — confirmed open, see above | committed |
| City Free Food & Meal Sites (ODP/ArcGIS) | City terms — confirmed open, see above | committed |
| USDA SRAM (2025 data, 2020 tracts) | US public domain | comparator |
| PDPH Neighborhood Food Retail | City terms | comparator (cited, not a metric input) |
| TIGER/Line 2025 + CenPop2020 | US public domain | committed |
| ACS 5-year 2020–2024 | Census terms (open) | committed |
| City Planning Districts | City terms | committed |
| SEPTA GTFS | Custom: revocable, redistribution permitted, fees reservable | committed (raw feed never republished) |
| OSM via Geofabrik | ODbL | committed (drives Bucket B) |

Excluded/blocked sources and fallback rules are recorded in
[roadmap/sources.md](../roadmap/sources.md). Notably, GoodRx is **blocked**
(ToS prohibits scraping/data mining) — no automated ingestion, caching, or
republication.

## What ships with each snapshot

For every acquired snapshot the manifest
(`raw/<source>/<snapshot-id>/manifest.json`, owned by the manifest engine
since EP-4a; field rules in [docs/data-dictionary.md](data-dictionary.md))
records: `acquisition_url` and `acquisition_url_alt` (dual URLs where a
provider is mid-migration); `terms_archive`, the file name of the archived
copy of the terms page in force, which must be one of the snapshot's
checksummed files; `license_bucket` (`A` or `B`, ADR-0003); `license_note`,
a human-readable summary of the terms; `schema_version`; and a SHA-256
digest per file. A manifest missing any of these is rejected and the
snapshot quarantined; `phillysim verify` re-checks every digest. This file
gains a dated entry per source as snapshots land.
