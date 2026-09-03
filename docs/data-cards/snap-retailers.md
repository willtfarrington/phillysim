# Data card: USDA SNAP Retailer Locator historical data (`snap_retailers`)

**Contributes.** The project's first destination source: every retailer in
Philadelphia County authorized to accept SNAP benefits as of the file's
as-of date, with USDA's own **store type** for each. The store type is what
the published mapping ([method card](../method-cards/store-formats.md))
turns into the format classes the destination layers use; the rows typed
`Supermarket` or `Super Store` are the **supermarket-format** layer
(Planning Baseline amendment AM-4), and the whole table is the
**all-SNAP-retailer** variant kept for the like-for-like comparison with
USDA's SNAP Retailer Access Map (SRAM) at M5.

**Provider and file.** US Department of Agriculture, Food and Nutrition
Administration (FNA; the Food and Nutrition Service, FNS, until 2026-06-01),
"SNAP Retailer Locator Historical Data":
`snap-retailer-locator-data2005-2025.zip` from
`https://www.fna.usda.gov/sites/default/files/resource-files/`, one member
`Historical SNAP Retailer Locator Data 2005-2025.csv` (UTF-8 with a
byte-order mark; 703,441 rows nationwide; columns Record ID, Store Name,
Store Type, Street Number, Street Name, Additional Address, City, State,
Zip Code, Zip4, County, Latitude, Longitude, Authorization Date, End Date).
Each row is one **authorization spell**: a record ID recurs when a store was
de-authorized and later re-authorized, and the end date is blank while the
authorization is open. The pre-rename URL on `www.fns.usda.gov` redirects to
the FNA one and is recorded as the manifest's alternate URL (the dual-URL
rule of [sources.md](../../roadmap/sources.md)); the FNA URL itself
redirects to a content-delivery host, which the adapter's allowlist names.

**Vintage.** "Current as of Dec. 31, 2025" (the provider's page, updated
2026-02-19); the file covers authorizations open at any point in 2005–2025.
Pinned snapshot `2026-09-02`, zip 24,036,753 bytes, stored as delivered.
USDA refreshes the historical file about once a year with a new year range
in the file name; a controlled refresh bumps `phillysim.pipeline.SNAPSHOT_ID`
and the adapter's URL and as-of date together. The as-of sentence is one of
the phrases the download path checks on the archived page, so a changed
vintage stops acquisition rather than delivering a different file silently.

**Terms and license.** US public domain (17 U.S.C. § 105): a work of the
United States Government, published by USDA as public data. **Bucket A**
(ADR-0003). There is no USDA terms page the guarded download path can
archive (the department's "Policies and Links" page, which states that USDA
web content is public domain, refuses non-browser clients with HTTP 403), so
the page archived beside the data is the provider's data page in force
(`https://www.fna.usda.gov/snap/retailer-locator/data`, archived as
`source-page.html`), checked for its official-US-government banner and its
as-of sentence. Citation: "U.S. Department of Agriculture, Food and
Nutrition Administration, SNAP Retailer Locator Historical Data 2005–2025
(as of December 31, 2025)". Store names are the provider's text and are
treated as untrusted on output (escaped, never interpreted).

**Coverage and filter.** Delivered nationwide; stored as delivered and
filtered at first read to `State = PA`, `County = PHILADELPHIA` (the
provider's own county attribution), and **open authorization spells only**
(blank end date), which leaves one row per record ID: 1,609 retailers as of
2025-12-31. Of the file's 8,709 Philadelphia rows over the twenty-year
window, the other 7,100 are closed spells. Blank cells become null;
coordinates become floats; everything else stays the provider's text.

**CRS.** Latitude and longitude are the provider's geocodes with no stated
datum; the adapter treats them as **WGS 84 (EPSG:4326)**, which differs from
NAD 83 in Philadelphia by far less than the geocoding error. The curated
layer keeps them as delivered in `longitude` / `latitude` and carries its
geometry in the analysis CRS EPSG:26918 (ADR-0007).

**Where it lands.** `curated/snap_retailers.parquet` (data dictionary,
"SNAP retailer layer"): site ID `snap_retailers:<Record ID>`, name, store
type, format class, supermarket-format flag, containing tract, coordinates,
authorization date, geometry; plus the stage report
`intermediate/snap_retailers.json` with the counts below.

**Real snapshot, 2026-09-02 (Philadelphia County, as of 2025-12-31).**

| Store type | Rows | Format class |
|---|---|---|
| Convenience Store | 631 | `convenience` |
| Small Grocery Store | 403 | `grocery` |
| Combination Grocery/Other | 190 | `combination` |
| Medium Grocery Store | 116 | `grocery` |
| Supermarket | 95 | `supermarket` |
| Super Store | 69 | `supermarket` |
| Meat/Poultry Specialty | 27 | `specialty` |
| Seafood Specialty | 26 | `specialty` |
| Large Grocery Store | 22 | `grocery` |
| Fruits/Veg Specialty | 16 | `specialty` |
| Farmers' Market | 7 | `farmers_market` |
| Bakery Specialty | 7 | `specialty` |
| **All** | **1,609** | 164 supermarket-format |

340 of the 408 tracts contain at least one authorized retailer and 115
contain at least one supermarket-format store. No `Delivery Route`,
`Food Buying Co-op`, `Military Commissary`, `Wholesaler`, or `Unknown` row is
open in Philadelphia at the as-of date (all five labels occur in the
county's closed spells or elsewhere in the file and are mapped anyway).

**Sanity check against the provider's own totals.** USDA's FY 2021 SNAP
Retailer Management Year End Summary reports 254,350 authorized firms
nationwide and 10,110 in Pennsylvania as of 2021-09-30; reconstructing that
date from the file's authorization and end dates gives 246,165 and 9,939
(3.2 % and 1.7 % lower). The FY 2017 national figure (263,105) reconstructs
as 254,861 (3.1 % lower). The gap is consistent with the two USDA store
types that never appear in the historical file, `Direct Marketing Farmer`
and `Internet Retailer`, which the year-end summaries count; no Philadelphia
figure is published to compare against directly, and the county's 1,609 sits
in the same ratio to the state's 9,818 open records as the FY 2021 figures
do. USDA's FY 2024 and FY 2025 summaries are interactive dashboards without
a static state table, so the FY 2021 PDF is the reference used.

**Known limits.**
- **Two retailers are geocoded outside every Philadelphia tract** (record
  IDs `873249` and `903932`, both `Target` stores that USDA attributes to
  Philadelphia County but whose coordinates fall in Montgomery County, one
  with city `ABINGTON`). They are kept in the layer with a null `geoid`, so
  the all-retailer count matches the provider; they enter no tract-level
  count. M4 conflation decides whether to drop or re-geocode them.
- **Thirteen pairs of retailers share identical coordinates** (the same
  building or the same geocoded address point); they are distinct
  authorizations and stay distinct rows. Cross-source de-duplication is M4.
- The provider's county attribution is administrative, not spatial; the
  layer's `geoid` comes from a point-in-polygon test against the spine, and
  the county filter uses the provider's field. No open Philadelphia-county
  row lies outside the county bounds, and no open row from another county
  carries a Philadelphia city name.
- USDA store types are self-reported at authorization and reviewed at
  reauthorization (about every five years); a store's type can lag a change
  in its format. The type says nothing about inventory, price, or hours
  (the file has no hours at all: `hours_status` will be `not_in_source`).
- Two store types on USDA's definitions page, `Direct Marketing Farmer` and
  `Internet Retailer`, are not in the file; two labels in the file,
  `Wholesaler` and `Unknown`, are not on the definitions page. The mapping
  covers the file's vocabulary; a new label fails the contract.

**Claims matrix.** Store categories are format-based and come from the
published USDA store-type mapping; no nutrition-quality adjective is applied
to them (C-2). Presence of a retailer is an access input, never a statement
about affordability, inventory, or suitability (C-1, C-2); counts per tract
are not scores (C-3).

**Checks that bind it.** Source contract (`phillysim.adapters.snap`: column
set, store type within the mapped vocabulary, Pennsylvania / Philadelphia
values, five-digit ZIP, WGS 84 points inside the county bounds, unique
record ID), the layer invariants (`phillysim.destinations.check_snap_layer`),
the golden mapping test, and the snapshot manifest.
