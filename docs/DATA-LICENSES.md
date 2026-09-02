# Data licenses

> **Status: first snapshots acquired (EP-5a, 2026-09-02); nothing published.**
> The three tract-spine sources have been acquired into the gitignored raw
> zone with their terms pages archived (dated entries below). This document
> states the licensing rules the project has adopted and gains a per-source
> record as each source is actually ingested. It mirrors the source matrix in
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
| TIGER/Line 2025 + CenPop2020 | US public domain | committed; acquired 2026-09-02 (records below) |
| ACS 5-year 2020–2024 | US public domain (summary file; API terms not engaged) | committed; acquired 2026-09-02 (record below) |
| City Planning Districts | City terms | committed |
| SEPTA GTFS | Custom: revocable, redistribution permitted, fees reservable | committed (raw feed never republished) |
| OSM via Geofabrik | ODbL | committed (drives Bucket B) |

Excluded/blocked sources and fallback rules are recorded in
[roadmap/sources.md](../roadmap/sources.md). Notably, GoodRx is **blocked**
(ToS prohibits scraping/data mining) — no automated ingestion, caching, or
republication.

## Snapshot records

One entry per source per acquisition, in the order acquired. Each names the
terms page archived beside the data (`terms_archive` in the manifest) and the
wording the download path checks for on every acquisition; if that wording
changes, the acquisition stops and the snapshot is quarantined
(`kind = "terms"`) until a person has read the new terms.

### 2026-09-02 — TIGER/Line 2025 census tracts (`tiger_tracts`), Bucket A

- **Acquired:** `https://www2.census.gov/geo/tiger/TIGER2025/TRACT/tl_2025_42_tract.zip`
  (Pennsylvania; Philadelphia County filtered at read), 13,109,450 bytes,
  stored as delivered.
- **Terms in force:** US public domain, a work of the United States
  Government (17 U.S.C. § 105). Archived beside the data: the Census Bureau
  Open Government page (`https://www.census.gov/about/policies/open-gov.html`,
  archived 2026-09-02 as `terms.html`), which states that the Bureau
  "publishes its data as open data, meaning it is freely available for use
  and re-use by the public"; the download path checks that sentence. The
  TIGER/Line 2025 technical documentation, section 1.2, adds that copyright
  protection is not available for the files and asks that the Census Bureau
  be cited as the source; section 1.1 notes that TIGER/Line® is a registered
  trademark and may not be used in a product name.
- **Attribution:** U.S. Census Bureau, TIGER/Line Shapefiles 2025.

### 2026-09-02 — CenPop2020 tract centers of population (`cenpop`), Bucket A

- **Acquired:** `https://www2.census.gov/geo/docs/reference/cenpop2020/tract/CenPop2020_Mean_TR42.txt`
  (Pennsylvania; county filtered at read), 144,662 bytes, stored as delivered.
- **Terms in force:** as for TIGER/Line: US public domain; the same Open
  Government page archived and checked.
- **Attribution:** U.S. Census Bureau, Centers of Population by Census Tract, 2020.

### 2026-09-02 — ACS 5-year 2020–2024, tables B01003 and B08201 (`acs`), Bucket A

- **Acquired:** `https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/`
  files `acsdt5y2024-b01003.dat` (18,313,708 bytes) and `acsdt5y2024-b08201.dat`
  (65,043,091 bytes), nationwide table files stored as delivered, county
  filtered at read. The data API was not used: on 2026-09-02 it redirected
  every key-less request to `missing_key.html`, so its Terms of Service (and
  the attribution notice they require) do not apply to this snapshot, and no
  key exists in the project.
- **Terms in force:** US public domain; the same Open Government page
  archived and checked.
- **Attribution:** U.S. Census Bureau, American Community Survey 5-Year
  Estimates 2020–2024, tables B01003 and B08201.

The committed CI samples under `phillysim/tests/fixtures/spine-samples/`
are subsets of these three snapshots (six Philadelphia County tracts plus
control rows) and inherit their public-domain status; their README says so.

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
