# Data licenses

> **Status: seven snapshots acquired (EP-5a, EP-6, and EP-8b, 2026-09-02;
> EP-12, 2026-09-03); the publish gate exists (EP-7); nothing published.**
> The three tract-spine sources, the USDA SNAP retailer file, the TIGER/Line
> county roads file for the basemap, and, since EP-12, the two routing
> sources (the OpenStreetMap extract via Geofabrik, the first **Bucket B**
> source of the real pipeline, and SEPTA's GTFS feed pinned to a release
> tag) have been acquired into the gitignored raw zone with their terms pages
> (or, for USDA, the provider's data page in force) archived (dated entries
> below), and the public zone the first five feed is built and gated locally
> but not tracked or deployed; nothing derived from the routing sources is
> published in the M3 spike. This
> document states the licensing rules the project has adopted and gains a
> per-source record as each source is actually ingested. It mirrors the
> source matrix in [roadmap/sources.md](../roadmap/sources.md); that matrix
> is the working record, this file is the shipped statement.

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

**How labels are applied (EP-7, 2026-09-02).** The `publish` stage
(`phillysim.publish`) derives every public file's bucket from the
`license_bucket` fields of the raw-snapshot manifests the file is built
from: Bucket B if any source is Bucket B, else Bucket A. No one labels a
file by hand. The label (bucket, SPDX identifier, license name and URL,
required notices) and the sources' citations are recorded per file in
`public/manifest.json` and, for GeoJSON, in the file itself (top-level
`license` and `attribution` members); Bucket B labels carry the ODbL notice
and "© OpenStreetMap contributors". The **publish gate**
(`phillysim.publish.gate`; `phillysim gate`) refuses a zone in which any
file's label differs from the derived bucket, an in-file label differs from
the manifest, a Bucket B file lacks its notices, a file is unlisted,
missing, or altered, a coordinate leaves WGS 84 or the declared bounds, a
CSV cell is unescaped, or any file mentions a pipeline path; the stage runs
it on the staged zone before the runner installs anything, and CI runs it
on the fixture's zone on every push. Field details are in the
[data dictionary](data-dictionary.md) ("Public zone").

**Labeling status (EP-7, 2026-09-02; EP-8b, 2026-09-03).** Nothing has
been published. Two public zones exist, both gitignored and gated green:
the fixture pipeline's (Bucket B throughout, because its synthetic
`osm_network` source is Bucket B; it is the CI evidence for the ODbL path)
and the real pipeline's thin slice (Bucket A, CC BY 4.0, derived from the
TIGER/Line tracts, CenPop, USDA SNAP, and, since EP-8b, TIGER/Line roads
snapshots; the ACS snapshot feeds nothing published yet). The EP-10
checkpoint (2026-09-03) traced every file of the real zone, rebuilt from a
fresh clone, to those four snapshots' manifests and the records below:
each file's bucket equals the bucket derived from its sources, the
attribution lines equal the adapters' citations and the records'
attribution entries, and the `license_note` texts equal the manifests'.
No file under any `public/` zone is tracked in the repository. The eight synthetic tinycity
manifests carry bucket labels (seven Bucket A; `osm_network` Bucket B, as
OSM-shaped content), and each source's contract pins its bucket: the
contract suite checks them on every test run and the `validate` stage on
every `phillysim run --fixture`.

**SEPTA-derived aggregates:** computed travel times are facts; published
matrices contain no GTFS feed contents. The raw feed is never republished,
and SEPTA's terms are re-read and archived at every refresh (EP-12 archived
and sentence-checked them at the first acquisition; record below).

**Routing sources and the buckets (EP-12, 2026-09-03).** The `network`
stage writes the first Bucket B output of the real pipeline,
`intermediate/network/` (the OSM extract clipped to the county bounds +
5 km beside SEPTA's two feed zips), labeled B by derivation from the
`osm_network` manifest (`intermediate/network.json` records the bucket and
the two source snapshots). Nothing downstream of it reaches `publish`
during the spike, so the public zone stays Bucket A; the first published
Bucket B files are M5's routing outputs, and the SEPTA feed's own bucket
is A (nothing OSM-derived comes from it).

## Source terms summary (to be expanded per snapshot)

| Source | License/terms | Status |
|---|---|---|
| USDA SNAP retailer file | US public domain | committed; acquired 2026-09-02 (record below) |
| City Farmers' Markets (ODP/ArcGIS) | City terms — confirmed open, see above | committed |
| City Free Food & Meal Sites (ODP/ArcGIS) | City terms — confirmed open, see above | committed |
| USDA SRAM (2025 data, 2020 tracts) | US public domain | comparator |
| PDPH Neighborhood Food Retail | City terms | comparator (cited, not a metric input) |
| TIGER/Line 2025 + CenPop2020 | US public domain | committed; acquired 2026-09-02 (records below) |
| TIGER/Line 2025 roads (basemap) | US public domain | committed; acquired 2026-09-02 (record below; EP-8b) |
| ACS 5-year 2020–2024 | US public domain (summary file; API terms not engaged) | committed; acquired 2026-09-02 (record below) |
| City Planning Districts | City terms | committed |
| SEPTA GTFS | Custom: revocable, redistribution permitted, fees reservable | committed; acquired 2026-09-03 (record below; EP-12); raw feed never republished |
| OSM via Geofabrik | ODbL | committed; acquired 2026-09-03 (record below; EP-12); drives Bucket B |

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

### 2026-09-02 — USDA SNAP Retailer Locator historical data (`snap_retailers`), Bucket A

- **Acquired:** `https://www.fna.usda.gov/sites/default/files/resource-files/snap-retailer-locator-data2005-2025.zip`
  (nationwide; Philadelphia County and open authorizations filtered at
  read), 24,036,753 bytes, stored as delivered. The manifest's alternate URL
  is the same path on `www.fns.usda.gov`, the pre-rename host (USDA's Food
  and Nutrition Service became the Food and Nutrition Administration on
  2026-06-01), which redirects to the FNA one; the FNA URL redirects in
  turn to a content-delivery host, which the adapter allowlists.
- **Terms in force:** US public domain, a work of the United States
  Government (17 U.S.C. § 105), published by USDA as public data. **No
  terms page could be archived through the guarded path:** USDA's
  "Policies and Links" page (`https://www.usda.gov/about-usda/policies-and-links`),
  which states that USDA web content is public-domain information that may
  be freely distributed or copied with acknowledgement, answers HTTP 403 to
  non-browser clients, and the FNA site carries no equivalent statement.
  Archived beside the data instead: the provider's data page in force
  (`https://www.fna.usda.gov/snap/retailer-locator/data`, archived
  2026-09-02 as `source-page.html`), which the download path checks for its
  "An official website of the United States government" banner and its
  "This data is current as of Dec. 31, 2025" sentence, so that a vintage
  change stops acquisition.
- **Attribution:** U.S. Department of Agriculture, Food and Nutrition
  Administration, SNAP Retailer Locator Historical Data 2005–2025 (as of
  December 31, 2025). Store type definitions: USDA "SNAP Store Type
  Definitions" (`https://www.fna.usda.gov/snap/store-definitions`).

### 2026-09-02 — TIGER/Line 2025 county roads, primary and secondary (`tiger_roads`), Bucket A

- **Acquired:** `https://www2.census.gov/geo/tiger/TIGER2025/ROADS/tl_2025_42101_roads.zip`
  (Philadelphia County, the provider's own county scope; primary and
  secondary roads, MTFCC S1100 / S1200, kept at read, the local streets
  dropped), 1,352,071 bytes, stored as delivered. Acquired on 2026-09-03
  UTC into the pinned `2026-09-02` snapshot beside the other Census
  sources (EP-8b).
- **Terms in force:** as for TIGER/Line tracts: US public domain, a work of
  the United States Government (17 U.S.C. § 105); the same Open Government
  page archived as `terms.html` and checked for the same sentence; the
  TIGER/Line 2025 technical documentation, section 1.2, on copyright and
  citation, and section 1.1 on the TIGER/Line® trademark.
- **Attribution:** U.S. Census Bureau, TIGER/Line Shapefiles 2025, roads.
- **Use:** the basemap only ([data card](data-cards/tiger-roads.md)); the
  published `basemap.geojson` (public schema version 2) carries the
  Bucket A label like every other file of the zone.

### 2026-09-03 — OpenStreetMap extract for Pennsylvania via Geofabrik (`osm_network`), Bucket B

The first Bucket B record.

- **Acquired:** `https://download.geofabrik.de/north-america/us/pennsylvania-260831.osm.pbf`
  (Geofabrik's **dated** Pennsylvania extract; OSM data as of
  2026-08-31T20:20:51Z by the region page, 2026-08-31T20:21:20Z by the
  file's own replication timestamp; never the `-latest` file), 345,912,530
  bytes, stored as delivered, with Geofabrik's MD5 sidecar
  `pennsylvania-260831.osm.pbf.md5` (62 bytes) fetched through the same
  guarded path and stored beside it. The delivered file's MD5,
  `a779d2ef14c8addce6eac207ab9cd851`, equals both the value pinned in the
  adapter ([ADR-0008](../roadmap/adr/0008-routing-toolchain-pins.md)) and
  the sidecar's; a mismatch of either quarantines the snapshot (kind
  `digest`). A PBF is not an archive and is never opened as one. The
  county filter is the clip the `network` stage writes (county bounds +
  5 km, way-complete); the state file never leaves the raw zone.
- **Terms in force:** the **Open Database License (ODbL) 1.0**
  (`https://opendatacommons.org/licenses/odbl/1-0/`); the data are
  © OpenStreetMap contributors, extracted and published by Geofabrik GmbH.
  Archived beside the data: the Geofabrik region page
  (`https://download.geofabrik.de/north-america/us/pennsylvania.html`,
  archived 2026-09-03 as `terms.html`), whose footer states that the
  extracts are "created by OpenStreetMap Contributors" under
  "License: ODbL 1.0"; the download path checks both phrases in the page's
  visible text.
- **Bucket:** **B**. Every file carrying a value computed over this
  network (the clipped extract in `intermediate/network/` today; the
  travel-time matrices and every metric column computed over them at M5)
  carries the ODbL label and the notice "© OpenStreetMap contributors";
  combined exports containing such a value are ODbL by rule (ADR-0003);
  rendered maps are Produced Works. Nothing derived from it is published in
  the M3 spike.
- **Attribution:** OpenStreetMap contributors, Pennsylvania extract
  pennsylvania-260831.osm.pbf via Geofabrik (ODbL 1.0).
- **Use:** the routing network ([data card](data-cards/osm-network.md));
  the routing spike (EP-13 onward) builds R5's street layer from the clip.

### 2026-09-03 — SEPTA GTFS, release v202609060 (`gtfs`), Bucket A

- **Acquired:** `https://github.com/septadev/GTFS/releases/download/v202609060/gtfs_public.zip`
  (SEPTA's GTFS as SEPTA publishes it on GitHub, release tag `v202609060`,
  published 2026-09-02; "Summer RR, Fall Bus-Metro, Sept Adjustments"),
  21,555,258 bytes, stored as delivered: one zip holding `google_bus.zip`
  (bus and Metro, authoritative 2026-09-06 to 2027-02-20) and
  `google_rail.zip` (Regional Rail, authoritative 2026-09-06 to
  2026-10-17). The delivered file's SHA-256,
  `4d3fa20ea094937a9bb6389ad52017e1ac90a564aee497f318797e1b1e4f07ab`,
  equals the digest GitHub records for the asset, pinned in the adapter;
  a mismatch quarantines the snapshot (kind `digest`). The outer zip was
  inspected (slip, bomb) at acquisition before anything was read out of
  it; each inner zip is inspected in place by the reader and again as a
  file when the `network` stage unwraps it. No county filter: the whole
  network is routing input (stops outside the routing box are counted,
  never dropped).
- **Terms in force:** SEPTA's developer license agreement, the text on
  `https://www3.septa.org/developer/` (archived 2026-09-03 as
  `terms.html`; "Agreement updated: Tue, 18 Mar 2014" by its own text).
  The download path checks two sentences, verbatim: "SEPTA reserves the
  right to alter and/or no longer provide the Trip Planning Data at any
  time without prior notice." and "SEPTA reserves the right to institute a
  license fee at any time in the future without prior notice." A change is
  the stop condition. The agreement is revocable, charges no fee today but
  reserves one, and forbids altering the data and commercial use of
  SEPTA's marks. **The project accepts those terms as archived:** the
  release download bypasses the page's click-through form by using SEPTA's
  own GitHub release, so the archived agreement text is what is accepted,
  and the terms are re-read and re-archived at every refresh.
- **Position (facts, not contents):** computed travel times are facts and
  carry no feed contents; no GTFS row, stop, or schedule is ever
  published, nothing unwrapped from the feed is ever copied under
  `public/` or `site/`, and the raw feed is never redistributed. The CI
  sample of this source is **synthetic** (a feed in SEPTA's layout over
  the six sample tracts), because committing any subset of the real feed
  to the repository would republish feed contents.
- **Bucket:** **A** for the feed itself: nothing OSM-derived comes from
  it. A travel time computed over the OSM network and this feed is
  Bucket B because of the network.
- **Attribution:** Southeastern Pennsylvania Transportation Authority
  (SEPTA), GTFS release v202609060.
- **Use:** the routing schedules ([data card](data-cards/septa-gtfs.md));
  the routing spike (EP-13 onward) builds R5's transit layer from the two
  feeds.

The committed CI samples under `phillysim/tests/fixtures/spine-samples/`
are subsets of the five Census and USDA snapshots (six Philadelphia County
tracts, the retailers and major roads inside them, plus control rows) and
inherit their public-domain status; the OSM sample is real OpenStreetMap
data (the extract clipped to the six tracts' bounds) committed under the
ODbL with the notice "© OpenStreetMap contributors" in the samples README
and in its Bucket B manifest; the GTFS sample is synthetic and carries no
SEPTA content. Their README says so.

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
