# Architecture

Local-first, CPU-only, single-maintainer proportionate. Windows 11 native is
the primary path; WSL2 is a documented fallback only. No Docker, PostGIS,
orchestrator, queue, GPU, cloud, or ML in v1 — each has an explicit upgrade
trigger (§Upgrade-only-when).

## Stack (locked; ADR-0001, ADR-0002)

- Python 3.12+ managed by uv (lockfile committed). Geo stack: GeoPandas /
  Shapely / pyproj with **pyogrio** I/O; the `GDAL` and `fiona` PyPI packages
  are banned from the dependency tree (sdist-only on Windows).
- DuckDB ≥1.1 + spatial extension as the local query engine; GeoParquet /
  Parquet across zones.
- r5py routing with project-local pinned Temurin JDK 21 (exact build,
  JAVA_HOME set per-invocation), R5 jar pinned by checksum, heap 12 GB.
- Typer-style CLI: `phillysim <stage>` over idempotent, manifest-checked
  stage functions; no orchestrator.
- Static site: MapLibre GL JS; project data as plain GeoJSON (~408 tracts,
  sub-MB gzipped — tiles don't pay off); minimal public-domain basemap
  (ADR-0005); local dev server; GitHub Pages artifact-only deploy.

## Data flow

```
authorized source adapters
  → immutable versioned snapshots (raw zone; checksummed manifests, terms archived)
  → schema + license validation (drift detection; quarantine on failure)
  → spatial/temporal normalization to the 2020-tract spine (intermediate zone)
  → destination-layer conflation + hours parsing (QA reports)
  → travel-time matrices (r5py)  → transparent metrics + MOE propagation (curated zone)
  → analytic tables {estimate, MOE, CV tier, reliability_action} + build-time bins
  → public-safe aggregates: license-bucketed GeoJSON/CSV (public zone)
  → static accessible site (map + parity table + methods/data cards)
```

Eleven pipeline stages with fingerprint-DAG semantics: each stage records
input fingerprints; unchanged inputs → skipped stage; resumable and safely
cancellable; early Philadelphia bounding-box filtering at ingest; preflight
checks (disk ≥150 GB free, RAM budget, dependency versions) before large
jobs.

The eleven stages, as registered by the fixture pipeline
(`phillysim.fixtures.pipeline`, EP-4b) and to be reused by name by the real
pipeline from EP-5a on (recorded at the EP-9 checkpoint, 2026-09-02):

| # | Stage | Data-flow step above | Output (zone) | Logic at EP-9 |
|---|---|---|---|---|
| 1 | `acquire` | authorized source adapters → immutable snapshots | `raw/<source>/<snapshot-id>/` | fixture: tinycity generated and admitted through the guards; real (EP-5a): TIGER / CenPop / ACS through the guarded download path (`phillysim.download`), pinned snapshot ID, existing snapshots re-used |
| 2 | `validate` | schema + license validation | `intermediate/validation.json` | source contracts (EP-3); real (EP-5a): each adapter's contract on the county-filtered read |
| 3 | `spine` | normalization to the 2020-tract spine | `curated/tracts_spine.parquet` | computed; real (EP-5b, `phillysim.spine`): TIGER geometry in the analysis CRS EPSG:26918 (ADR-0007) + CenPop population and centers, invariants enforced in-stage |
| 4 | `demographics` | normalization (ACS estimates + MOE on the spine) | `intermediate/acs_tracts.parquet` | computed; real (EP-5b): pinned ACS variables + MOE joined one-to-one, nulls kept |
| 4b | `snap_retailers` (real pipeline only, EP-6) | normalization (one destination source classified and assigned to tracts) | `curated/snap_retailers.parquet` | real: USDA SNAP retailers as of the file's as-of date, store-format classification from the published mapping (`phillysim.classify`), tract assignment, stable site IDs, invariants enforced in-stage; the fixture has no per-source layer stages (its `destinations` reads the fake sources directly), and M4 adds one per destination source before `destinations` |
| 5 | `destinations` | normalization (destination points assigned to tracts) | `intermediate/destinations.parquet` | computed (fixture); real: M4, over the per-source layers |
| 6 | `conflate` | destination-layer conflation | `intermediate/sites_conflated.parquet` | identity stub until M4 |
| 7 | `hours` | hours parsing | `curated/sites.parquet` | oracle stub until M4 |
| 8 | `network` | routing inputs (GTFS + street network) | `intermediate/network.json` | computed summary |
| 9 | `travel_times` | travel-time matrices | `curated/travel_times.parquet` | precomputed stub until M3 |
| 10 | `metrics` | transparent metrics + MOE propagation → analytic table | `curated/tract_metrics.parquet` | fixture: computed (CV tiers, time to nearest); real (EP-7, `phillysim.metrics.slice`): the QA-only straight-line slice metric to the nearest supermarket-format retailer, in the locked analytic shape; M5 replaces the body and keeps the column as QA |
| 11 | `publish` | public-safe aggregates: license-bucketed GeoJSON/CSV (public zone) | `public/` (the whole zone, one atomic install: `manifest.json`, `tracts.geojson`, `tracts.csv`, `sites.geojson`, `sites.csv`) | both pipelines (EP-7, `phillysim.publish`): the analytic table widened onto the tracts with build-time bins, facility points, per-file license labels derived from the sources' manifests (ADR-0003), CSV formula-injection escaping, WGS 84, and the publish gate run on the staged zone before install; `phillysim gate` re-checks an installed zone (CI runs it on the fixture) |

The static site is built from the public zone and is not a pipeline stage.

## Zones & identifiers

`data/raw/<source>/<snapshot-id>/` (immutable) → `data/intermediate/` →
`data/curated/` → `data/public/` (the only zone that ever reaches the repo or
site). Snapshot ID = date-stamped per-source identifier recorded in a
checksummed manifest (acquisition URL + dual-URL field, terms archive,
schema version, license bucket). Canonical keys: GEOID (2020), source-scoped
site IDs from conflation.

## Resource budgets (validated at the M3 spike)

Routine peak RAM ≤24 GB; routing budget measured as peak **sum of RSS across
the pipeline process tree** (sampled ≥1 Hz): budget 20 GB, kill 22 GB.
Workspace ≤50 GB under the app-owned `data/` root; preflight requires
≥150 GB free disk; default parallelism ≤8 of 16 logical processors; GPU
unused. Long routing runs execute unattended (overnight) — session time and
wall-clock are accounted separately.

## Security (proportionate threat model)

Untrusted-input controls: size/schema/content validation and quarantine on
all downloads; zip-slip and decompression-bomb guards; CSV formula-injection
escaping on exports (source-derived names are the untrusted vector); popup/
panel output escaping; outbound domain allowlist + timeouts/backoff;
localhost-only dev services; minimal CI token permissions; secret scanning +
push protection; pinned CI actions; lockfiles. Explicitly not applicable
(with rationale recorded): server auth, multi-tenancy, SSRF beyond the
allowlist — no server exists.

## Upgrade-only-when triggers `required roadmap decision`

- PostGIS: concurrent writers, data beyond memory-practical scale, or network
  topology operations DuckDB cannot express.
- Orchestrator: >3 interdependent scheduled flows or multi-machine execution.
- Docker: a reproducibility failure traceable to host environment that
  pinning cannot fix.
- GPU/ML: a validated method requiring it, with its own evidence gate.
- Cloud: a collaboration or scale need that a static site cannot meet.

## Rejected alternatives (summary; details in ADRs)

PostGIS-first, orchestrator-first, Docker-first (prestige without need);
project-data vector tiles (below size threshold); pandana fallback (no
py3.12 Windows wheels); PMTiles-first basemap (critical-path simplification,
ADR-0005); scrollytelling UI; Streamlit/Dash (server + weaker a11y control);
hour-based estimates.
