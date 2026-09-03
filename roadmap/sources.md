# Source feasibility & licensing matrix

All terms verified on live first-party pages 2026-08-23 (Phase B WS2 +
red-team spot-verification). Statuses: **committed** (v1), **comparator**,
**gated** (future module), **excluded**, **blocked**. Per-source terms are
archived with each snapshot; manifests carry dual URLs where providers are
mid-migration. `required release evidence`: DATA-LICENSES document mirroring
this matrix ships with the repo.

| Source | Role | License/terms | Status | Notes |
|---|---|---|---|---|
| USDA SNAP retailer file | Supermarket-format destination points (typed store formats) | US public domain | committed; acquired 2026-09-02 (EP-6) | Point-level; classification vocabulary format-based only; FNS→FNA rename 2026-06-01 handled by dual URLs; no USDA terms page reachable by the guarded path (data page archived instead; DATA-LICENSES) |
| City Farmers' Markets (ODP/ArcGIS) | Market destinations, day/season fields | City of Philadelphia terms (see caveat) | committed | Free-text hours → parser + QA packet |
| City Free Food & Meal Sites (ODP/ArcGIS) | Meal-site destinations, structured per-day hours | City terms (see caveat) | committed | Delisting policy applies (governance.md) |
| USDA SRAM (2025 data, 2020 tracts) | External comparator | US public domain | comparator | Like-for-like vs project all-SNAP-retailer variant ONLY; universe = all SNAP retailers incl. convenience/dollar |
| PDPH Neighborhood Food Retail | Prior art / comparator | City terms | comparator | Polygon aggregates on 2010 GEOIDs, no store points/hours — not a metric input; cite and complement |
| TIGER/Line 2025 + CenPop2020 | Tract spine + population-weighted centroids | US public domain | committed | ODP census-tract record is 2010-only — not used |
| ACS 5-year 2020–2024 | Denominators, demographics, MOE | Census terms (open) | committed | Pinned vintage per snapshot |
| City Planning Districts | Context geography | City terms | committed | |
| SEPTA GTFS | Transit schedules for routing | Custom: revocable, redistribution permitted, fees reservable | committed | Pin release tags; never republish the raw feed; re-read terms each refresh; derived aggregates position: matrices contain no feed contents — computed travel times are facts (documented in DATA-LICENSES) |
| OSM via Geofabrik | Street network; supermarket cross-check | ODbL | committed | Share-alike: see license buckets below |
| Basemap (v1) | Minimal public-domain cartography: county boundary (dissolved from the TIGER tract spine) + TIGER/Line 2025 primary and secondary roads (`tiger_roads`, the county roads file filtered to MTFCC S1100 / S1200) | US public domain | committed; acquired 2026-09-02 (EP-8b); published as `basemap.geojson` (public schema 2) | AM-5; no City layer needed for v1; PMTiles upgrade gated (scope.md, OQ-F) |
| Archived Philly Food Access 2012–14 | — | — | excluded | Stale; provider marks non-comparable |
| CostQuest BDC Fabric | — | Licensed, BDC-purposes-only | excluded | Not needed |
| NPPES pharmacy locations | Future pharmacy-access module | US public domain | gated | |
| FCC BDC public summaries + ACS internet tables | Future telehealth module | Open | gated | |
| GoodRx (prices) | — | ToS prohibits scraping/data mining | **blocked** | No automated ingestion/caching/republication absent an expressly applicable API/license |

**OpenDataPhilly umbrella:** the catalog licenses nothing; each originator's
terms govern acquisition, derivatives, and redistribution.

**City of Philadelphia license position (confirmed in writing 2026-09-02):**
the operative City text reserves all rights and contains no express grant;
reuse relies on the open-data publication context ("Public Use; Free" record
markings, the program's purpose). That reading was confirmed by CityGeo
(Office of Innovation & Technology), the office running the Open Data
Program: no terms exist beyond the published open-data terms page, and the
data is shared for people "to use in any way they want to benefit the
community" (OQ-A, closed). DATA-LICENSES records the reply. Per-snapshot
terms archiving and takedown readiness remain standing policy; the reply is
archived beside the terms page with the first City snapshot.

## License buckets for published outputs (AM-1)

- **Bucket A (CC BY 4.0):** prose, method/data cards, and derived tables
  containing no OSM-derived contents.
- **Bucket B (ODbL):** any table containing OSM-derived contents (travel-time
  matrices, metric columns computed over the OSM network) — including **every
  combined export** (table CSVs, the site's GeoJSON payloads), by rule.
  In-file/sidecar attribution: ODbL + "© OpenStreetMap contributors."
  Rendered maps are Produced Works (attribution notice only).
- Public-domain inputs impose nothing; carrying ACS columns inside an ODbL
  file creates no conflict.
- CI validates per-file license labels in `data/public/` **and** site data
  payloads at the publish gate (since EP-7: buckets are derived from the
  sources' manifests, never assigned by hand; `phillysim gate`).

## Refresh & drift strategy

Versioned immutable snapshots; manual controlled refresh only; schema-drift
detection on every acquisition; terms pages re-read and archived at each
refresh (SEPTA explicitly). Known drift risks: USDA FNS→FNA domain migration
(dual URLs in manifests); ArcGIS Hub URL churn; city dataset deprecations.
Fallbacks: OSM `shop=supermarket` if the SNAP file access changes; walk-only
metrics if SEPTA terms become unusable; feature removal + changelog as last
resort. A source disappearing does not break reproducibility of published
releases (derived tables remain), per the scoped reproducibility claim.
