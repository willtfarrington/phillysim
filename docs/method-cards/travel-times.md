# Method card: network travel times to SNAP retailers (stub, EP-15)

> **Status: stub (EP-15, 2026-09-03; the verdict recorded as go on
> 2026-09-04). The matrix exists in the curated zone since the
> `travel_times` stage's first night and is not published.** M5 completes
> this card when a travel-time metric is published; until then the numbers
> below describe the M3 routing spike's evidence, not a public claim. Access
> is *measured* as travel time (C-1); nothing here is a score, a rank, or a
> statement about a store's stock, prices, or suitability (C-2, C-3), and a
> tract-level time is never an individual's (C-4).

## What this method does

For each of Philadelphia County's 408 2020 census tracts, from the tract's
2020 population-weighted center as published by CenPop2020 (the spine's
`centroid_lon` / `centroid_lat`; [data card](../data-cards/cenpop.md)), to
every one of the 1,609 SNAP-authorized retailers in the county as of the
pinned file ([data card](../data-cards/snap-retailers.md); the 164
supermarket-format rows are a subset by the
[store-format method card](store-formats.md)), the routing engine computes:

- **walk**: the network walking time at **4.8 km/h** (the slow-walk
  sensitivity at 3.0 km/h is timed, not published, until M5);
- **walk+transit**: the door-to-door time by walking and SEPTA transit,
  departing every minute from **08:00 to 20:00** on the pinned typical
  Wednesday, **2026-09-23** (the Saturday window, 2026-09-26, is M5's),
  summarized as the **typical time** (the median over the 720 departures)
  and the **time on slower departures** (the 85th percentile).

Times are integer minutes, **censored at 120**: a pair with no route within
120 minutes reads 120 in both columns, and nothing exceeds it. The table is
`curated/travel_times.parquet` in the shape of the
[data dictionary](../data-dictionary.md) ("Travel-time matrix"): one row per
origin × destination × mode.

## Engine, pins, and parameters

- **Engine:** Conveyal R5 through r5py, on a project-local Eclipse Temurin
  JDK 21.0.12.1+1 and the jar `r5-v7.5.1-r5py-all.jar`, both pinned by
  digest ([ADR-0008](../../roadmap/adr/0008-routing-toolchain-pins.md));
  r5py 1.1.7; heap 12 GB; 8 of 16 logical processors; every run a sampled
  child process with a run record (`phillysim.routing`).
- **Street network:** OpenStreetMap via Geofabrik's dated Pennsylvania
  extract `pennsylvania-260831.osm.pbf` (data as of 2026-08-31), clipped to
  the county bounds buffered by 5 km ([data card](../data-cards/osm-network.md));
  ODbL, so every table computed over it is **Bucket B** by derivation
  ([ADR-0003](../../roadmap/adr/0003-license-buckets-odbl.md)) and the
  public zone stays Bucket A until M5 publishes a travel-time metric.
- **Transit:** SEPTA's GTFS release `v202609060`, bus/metro and Regional
  Rail ([data card](../data-cards/septa-gtfs.md)); computed times are facts
  and carry no feed contents.
- **Points snapped to the network** (r5py `snap_to_network`); origins and
  destinations leave the analysis CRS as WGS 84 only at the engine's
  boundary ([ADR-0007](../../roadmap/adr/0007-analysis-crs.md)).
- **Methods axis:** the plan file `travel-times.json` (its digest and every
  run's parameters are the stage's parameters); a change re-runs routing and
  bumps the methods version ([ADR-0006](../../roadmap/adr/0006-versioning-axes.md)).

## Evidence from the M3 spike (night `20260903T223607Z-m3-spike`, 2026-09-03)

| Criterion (source) | Measured | Status |
|---|---|---|
| Wall ≤ 8 h, the two core runs together (milestones.md; ADR-0008) | 830 s (walk 54 s + walk+transit 776 s); all seven runs 47 min | pass |
| Process-tree RSS ≤ 22 GB; peak against the 20 GB budget (milestones.md; architecture.md) | peak 5.39 GB, no run near the budget | pass |
| Determinism within band (milestones.md; ADR-0008 / OQ-C) | both core runs against their repeats: 656,472 of 656,472 pairs identical in both columns, byte and canonicalized-value digests equal | pass; the measured band is zero |
| ≥ 95 % finite pairs, walk+transit core run (methodology.md) | 99.95 % (300 pairs of 656,472 at the censor); every origin reaches a retailer | pass |
| ≥ 95 % finite pairs, walk core run (methodology.md) | 46.95 % under the 120-min censor; the straight-line reach bound at 4.8 km/h admits at most 56.24 % of the pairs (a walk of 120 minutes covers 9.6 km; the county spans 27 × 28 km), so no engine can meet the gate for walk over all 1,609 retailers under this censor; 83.5 % of the pairs the bound admits are finite; every origin has a finite pair | reported, not judged: the gate is read on the walk+transit run (owner decision at EP-15, recorded in methodology.md "Validation") |
| Walk-network concordance ρ ≥ 0.95 against the fallback engine (methodology.md) | Spearman ρ = 0.9935 over 28,256 pairs both engines report under the censor (of 408 × 164 supermarket-format pairs; OSMnx 2.1.1 + scipy 1.18.1 on the same clip); median absolute difference 0.8 min | pass |
| ≥ 80 % of hand-checked OD times within tolerance, 32 of 40 (methodology.md; ADR-0008) | 34 of 40 within tolerance (walk 14 of 20, walk+transit 20 of 20; ten pairs by rule, 08:30 and 17:30, both modes, compared by hand against SEPTA's planner and a general planner, 2026-09-04); the six misses are walk checks where the project's time is 5 to 8 minutes under the planner's on 10- to 21-minute trips, and over all twenty walk checks the project is never slower than the planner (median difference −3.5 min): R5 at a flat 4.8 km/h is faster than a consumer planner's walking estimate on short trips, a finding for the M5 card | pass |

## What it is not

- **Not a statement about a store** (C-2): "SNAP-authorized" and
  "supermarket-format" are USDA's store types, format-based only.
- **Not a score, rank, or index** (C-3); components are exposed one at a
  time, and no travel-time column is published before M5.
- **Not individual risk** (C-4): a tract-level time from a population
  center says nothing about any resident.
- **Not a prediction**: a pinned schedule on a pinned day; a refresh of the
  feed or the extract is a new snapshot and a methods-version bump.
