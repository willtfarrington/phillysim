# Method card: QA straight-line distance to the nearest supermarket-format retailer

> **Status: QA-only (EP-7, 2026-09-02). This is not an access measure and
> will never be published as one.** [methodology.md](../../roadmap/methodology.md)
> ("Travel model") fixes that straight-line distance is computed only as a
> QA column; the project's access measures are network travel times, which
> arrive with the routing spike (M3) and the metrics milestone (M5). This
> card exists because the column exists, so that its meaning is pinned in
> the same place every other method's is.

## What this method does

For each of Philadelphia County's 408 2020 census tracts, the `metrics`
stage of the real pipeline (`phillysim.metrics.slice`, methods version
`slice-qa-1`) takes the tract's 2020 population-weighted center as published
by CenPop2020 ([data card](../data-cards/cenpop.md); the spine's
`centroid_lon` / `centroid_lat`, the routing origin), projects it into the
analysis CRS EPSG:26918 ([ADR-0007](../../roadmap/adr/0007-analysis-crs.md),
metres), and records the Euclidean distance in that plane to the nearest
point of the supermarket-format SNAP retailer layer (the rows of
`curated/snap_retailers.parquet` with `supermarket_format` true; 164 for the
pinned snapshot; [store-format method card](store-formats.md),
[SNAP data card](../data-cards/snap-retailers.md)). The distance is rounded to
a tenth of a metre. It is written as one row per tract in the analytic table
(metric ID `qa_straight_line_m`, category `supermarket_format`, no mode, no
margin of error, no CV tier) and published as the column
`qa_straight_line_m__supermarket_format` with its build-time quintile bin
([data dictionary](../data-dictionary.md), "Public zone").

## Why it exists

The thin vertical slice (roadmap [scope.md](../../roadmap/scope.md)) needs one
number per tract to carry from the curated zone through the publication
boundary, so that the license labeling, the build-time bins, the CSV
escaping, the publish gate, and (EP-8) the page are proven end to end before
any real metric exists. The simplest honest number is this one: it uses only
the two curated layers that exist, needs no network, and is trivially
checkable by hand. When the real metrics land, the column stays in the
analytic table as a quality-assurance column (a sanity bound: a tract's
network travel time to the same layer can never correspond to a shorter
straight-line distance) and nothing more.

## What it is not

- **Not access.** Straight-line distance ignores streets, rivers, rail
  yards, highways, and transit; it is not the walk or walk-plus-transit time
  the project measures (C-1: the project measures access; this column does
  not).
- **Not a score, rank, or index** (C-3). Its bins are display classes for a
  choropleth, computed at build time; they rank nothing.
- **Not a statement about the store** (C-2): "supermarket-format" is USDA's
  store type, format-based only.
- **Not individual risk** (C-4): a tract-level distance from a population
  center says nothing about any resident.

## How the honesty is enforced, not promised

- The metric ID starts with `qa_`; the public manifest flags every such
  field `qa_only` and carries a note saying QA columns are not access
  measures; the publish gate rejects a `qa_` column that is not flagged, a
  flagged field whose description does not say QA, and a manifest without
  the note.
- The column's description in the manifest begins "QA-only plumbing check,
  not an access measure".
- The site (EP-8, M6) must render this column under that description or not
  at all; the claims-compliance sweep (release checklist, quality.md) checks.

## Real snapshot, 2026-09-02

Sources TIGER/Line 2025, CenPop2020, USDA SNAP retailers as of 2025-12-31
(all Bucket A, so the public zone is CC BY 4.0). 408 tracts, 164
supermarket-format destinations, no null distance. Distance from the
population-weighted center to the nearest supermarket-format retailer:
minimum 35.3 m, median 622.5 m, maximum 3,150.6 m (`intermediate/slice_metric.json`).
Quintile edges recorded in the public manifest: 35.3, 355.5, 544.14,
767.98, 1,047.02, 3,150.6 m.
