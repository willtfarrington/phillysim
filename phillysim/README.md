# phillysim (package)

The Python package and uv project for phillysim. The repository root holds the
governance documents and roadmap; this directory holds the code. Read the
[repository README](../README.md) first for what the project is and is not.

## Setup (Windows-native is the primary path)

Requires [uv](https://docs.astral.sh/uv/). uv installs the pinned CPython
(`.python-version`, currently 3.13; the package declares `>=3.12`) on first
sync, so no system Python is needed or used.

```
cd phillysim
uv sync --locked
uv run phillysim --help
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run pre-commit install        # once per clone; hooks live in ../.pre-commit-config.yaml
```

Every runtime dependency installs from binary wheels on Windows (ADR-0001).
WSL2 is a documented fallback only; the CI matrix also runs the suite on Linux.

On Windows, clone with `git clone -c core.longpaths=true …` (or set
`git config --global core.longpaths true` first). Two file names under the
repository's vendored `source material/` tree exceed the default
260-character path limit once the clone sits in a directory path longer
than about 130 characters; the checkout fails otherwise (found at the EP-9
checkpoint's fresh-clone re-run).

## Layout

```
phillysim/
  pyproject.toml          project metadata, locked stack, ruff/pytest config
  uv.lock                 committed lockfile (dependency version axis, ADR-0006)
  src/phillysim/
    cli.py                Typer entry point: `phillysim <command>`
    config.py             data-root resolution and zone paths
    zones.py              zone layout, source / snapshot-ID rules, snapshot listing (EP-4a)
    manifest.py           snapshot manifest model, canonical reader/writer, verify (EP-4a)
    guards.py             download guards: allowlist, size cap, zip-slip, bomb (EP-4a)
    quarantine.py         default-deny admission; failed snapshots move to quarantine/ (EP-4a)
    stages.py             stage registry: Stage / Pipeline declarations, cancel token (EP-4b)
    runner.py             fingerprints, state file, skip / resume / cancel, status, verify (EP-4b)
    preflight.py          disk / RAM / dependency / writable-root checks before a run (EP-4b)
    download.py           the guarded outbound acquisition path: allowlist, https, timeout +
                          bounded backoff, capped streaming, archive guards, terms archive,
                          manifest, admission (EP-5a)
    adapters/             real source adapters: base (Adapter, Philadelphia constants),
                          tiger, cenpop, acs (EP-5a), snap (USDA SNAP retailers, EP-6),
                          tiger_roads (TIGER county roads for the basemap, EP-8b);
                          ADAPTERS registry
    basemap.py            the basemap's roads layer on the spine and its invariants (EP-8b)
    classify/             project-derived, format-based classifications: store_format
                          (USDA store type -> format class, the packaged, versioned
                          mapping table rendered into docs/method-cards/) (EP-6)
    destinations.py       destination layers on the spine: the classified SNAP retailer
                          point layer and its invariants (EP-6)
    metrics/              metrics on the spine: slice (the QA-only straight-line slice
                          metric, the analytic table's first real instance) (EP-7)
    publish/              the publication boundary: bucket (ADR-0003 labels derived from
                          the sources), bins (build-time classes), export (the public
                          zone: labeled, escaped, deterministic GeoJSON + CSV + manifest),
                          gate (what must hold before anything leaves curated) (EP-7;
                          the basemap file and public schema version 2, EP-8b);
                          sitebuild (the slice page built from a gated zone, the local
                          dev server) (EP-8a)
    routing/              the routing toolchain and harness (EP-13; ADR-0008): toolchain
                          (the pinned Temurin JDK 21 and R5 jar installed project-local
                          through the guarded path, `toolchain install` / `check`), sampler
                          (process-tree RSS at >= 1 Hz, the 20 GB budget line and the
                          22 GB kill), records (run plans and the scrubbed run record under
                          `<data root>/runs/routing/`), harness (every JVM run in a child
                          process with a per-invocation environment; the only module that
                          imports r5py, inside the child), smoke (the first route, three
                          times)
    pipeline.py           the real pipeline: `acquire` + `validate` (EP-5a), `spine` +
                          `demographics` (EP-5b), `snap_retailers` (EP-6), `basemap`
                          (EP-8b), `metrics` + `publish` (EP-7) on the pinned snapshots
    spine.py              the curated tract spine, the analysis CRS (ADR-0007), and the
                          geospatial invariants every later packet inherits (EP-5b)
    contracts.py          source-contract harness (schema/license/geometry) + the
                          locked analytic-table contract
    fixtures/tinycity.py  deterministic synthetic fixture generator (EP-3)
    fixtures/tinycity_contracts.py   contracts for the eight fake sources
    fixtures/pipeline.py  the eleven fixture stages behind `phillysim run --fixture` (EP-4b)
  tests/
    conftest.py           fixture-directory paths; the suite-wide no-network guard
    test_smoke.py         package import + CLI help/version/paths
    test_config.py        data-root resolution rules
    test_zones.py         snapshot-ID / source-name rules, layout creation, listing
    test_manifest.py      round-trip, field rules, snapshot + zone verification, `verify --raw`
    test_guards.py        one crafted malicious input per guard; admission + quarantine
    test_download.py      every branch of the download path on a fake transport (EP-5a)
    test_runner.py        registry rules, fingerprints, skip / resume / cancel, status, verify
    test_preflight.py     every check reported in one pass; simulated failures refuse the run
    test_dependency_policy.py   GDAL/fiona ban, with built-in negative checks
    test_tinycity_fixture.py    determinism + committed-golden checks
    test_spine_invariants.py    geospatial invariants on the samples (CI) and, with
                                `--real-data-root DIR`, on the real spine (manual) (EP-5b)
    test_store_format.py        golden mapping test: the store-type table, its rules, and
                                the method card it renders into (EP-6)
    test_destinations.py        the SNAP retailer layer on the samples and its invariants,
                                one negative per check (EP-6)
    test_basemap.py             the basemap roads layer on the samples and its invariants,
                                one negative per check, the stage body; the real layer with
                                `--real-data-root DIR` (EP-8b)
    test_slice_metric.py        the QA slice metric: golden distances by hand, a brute-force
                                check on the samples, the rules that keep it QA-only (EP-7)
    test_publish.py             buckets, bins, escaping, the export, and the publish gate:
                                green on the fixture's zone, one negative per check (EP-7);
                                the basemap file and its gate rules (EP-8b)
    test_sitebuild.py           the site build: verbatim copies (the basemap among them),
                                vendored digests, determinism, refusals, CLI, the dev
                                server (EP-8a, EP-8b)
    test_site_browser.py        the fixture-built page and the sample-built real page in
                                the machine's own Chrome or Edge: Playwright + axe,
                                keyboard, reflow, fallbacks, the basemap's measured
                                contrast table (EP-8a, EP-8b)
    test_toolchain.py           the pinned toolchain installed from crafted archives on a
                                fake transport: digests, zip-slip, bomb, the Java version,
                                the Linux tarball path, idempotence, `check` (EP-13)
    test_sampler.py             the RSS sampler on a scripted profile and on real scripted
                                children (the kill at the line, the grandchild) (EP-13)
    test_records.py             run plans, run IDs, the scrub, the canonicalized-value and
                                byte digests (EP-13)
    test_routing_harness.py     the child's environment and r5py arguments; the run loop on
                                scripted children: completed, failed, killed-rss (EP-13)
    test_no_jvm_in_ci.py        no module imports r5py or JPype at module level, only the
                                harness child anywhere; the group is optional; CI installs
                                none of it; the ignore rules; nothing tracked (EP-13)
    test_performance_smoke.py   `phillysim run --fixture` under the sampler: wall and peak
                                RSS bounds, the numbers in the test log (EP-13)
    contracts/            harness unit tests; tinycity sources; the three spine sources,
                          the SNAP retailer source, the TIGER roads source, and the two
                          routing sources on the committed samples (EP-5a, EP-6, EP-8b,
                          EP-12)
    integration/          tinycity through all eleven stages via the CLI (M1 evidence); the
                          real pipeline's nine stages on a fake transport (EP-5a–EP-12)
    fixtures/tinycity/    golden fixture (README explains the layout)
    fixtures/tinycity-invalid/  injected-fault variant for negative tests
    fixtures/spine-samples/     real-shaped subsets of the seven real snapshots (five
                                public-domain, the OSM clip under ODbL, a synthetic GTFS
                                feed) + the script that cuts them (README explains)
```

## The tinycity fixture

CI is offline by policy, so every pipeline stage is exercised on a synthetic
mini-geography instead of real data. `phillysim gen-tinycity --out DIR`
regenerates it deterministically; the committed copy under
`tests/fixtures/tinycity/` is checked against a fresh generation on every test
run. See [tests/fixtures/tinycity/README.md](tests/fixtures/tinycity/README.md)
for what it contains and [docs/data-dictionary.md](../docs/data-dictionary.md)
for the columns.

## Data root

The app owns one `data/` root with zones `raw`, `intermediate`, `curated`,
`public` (plus `quarantine` and `cache`). It resolves, in order, from the
`PHILLYSIM_DATA_ROOT` environment variable, then `<repo root>/data`, then
`<cwd>/data`. No absolute path is ever hard-coded; `phillysim paths` shows
the resolution without creating anything. Only `data/public/` may ever be
committed, and only via the publish gate ([docs/DATA-LICENSES.md](../docs/DATA-LICENSES.md)).

## Raw snapshots, manifests, and guards (EP-4a)

Every acquisition lands as an immutable snapshot directory
`data/raw/<source>/<snapshot-id>/` holding the acquired files, the archived
terms page, and a `manifest.json` in the shape documented in
[docs/data-dictionary.md](../docs/data-dictionary.md) (acquisition URL and
alternate URL, terms archive, license bucket, schema version, per-file
SHA-256). Snapshot IDs are the acquisition date, `YYYY-MM-DD`, with `-1`,
`-2`, … for a further acquisition the same day; existing snapshots are never
overwritten.

A staged snapshot enters the raw zone only through `phillysim.quarantine.admit`,
which is default-deny: the manifest must parse, the recorded URLs must be on
the adapter's domain allowlist (https only, no credentials, no IP literals),
every file must sit under the size cap, any zip must pass the zip-slip and
decompression-bomb checks, and every digest must match. On any failure the
whole directory moves to `data/quarantine/<source>/` with a reason file
beside it, and nothing there is ever read again. The guards
(`phillysim.guards`) work on local files and are tested only against crafted
inputs; no test or command in this package reaches the network.

`phillysim verify` checks every snapshot in the data root's raw zone against
its manifest and exits non-zero on the first tampered byte, missing or
unlisted file, or stray entry; `--raw DIR` checks any raw-zone directory on
its own. `verify` also checks the stage state (next section).

## Pipeline: stages, fingerprints, state, resume (EP-4b)

The pipeline is a fixed sequence of idempotent stages
(`phillysim.stages.Pipeline`), each a plain function that declares its inputs
and outputs as data-root-relative paths (`raw/<source>/<snapshot-id>`,
`curated/tracts_spine.parquet`, …) and a mapping of parameters. There is no
orchestrator. The runner (`phillysim.runner`) computes each stage's
**fingerprint** as the SHA-256 of its inputs' content digests plus its
parameters, nothing more, and records it in the state file
`<data root>/pipeline_state.json` ([shape](../docs/data-dictionary.md)).

- `phillysim run [--fixture] [--data-root DIR] [--stage NAME] [--param stage.key=value …]`
  runs preflight, then every stage in order, **skipping** any stage whose
  recorded fingerprint equals the current one and whose outputs are still on
  disk unaltered. A stage writes into `cache/staging/<stage>/` and the runner
  installs each output into its zone with an atomic rename only after the
  stage has finished, so a crash or cancellation never leaves a partially
  written file in a zone. `--stage NAME` stops after that stage; `--param`
  overrides a declared parameter (JSON value or string; unknown keys are
  refused) and, because parameters are part of the fingerprint, re-runs that
  stage and any downstream stage whose inputs then change in content.
- `phillysim status [--fixture]` prints each stage as **fresh** (fingerprint
  unchanged, outputs intact), **stale** (an input, a parameter, or an output
  changed), **missing** (never run, or an output is gone), or **incomplete**
  (the last attempt failed or was cancelled). Creates nothing.
- `phillysim verify [--fixture]` runs the EP-4a snapshot check on the raw zone
  and then checks the state file against the zones: every `done` stage's
  outputs present with their recorded digests, no stage left running,
  failed, or cancelled, no leftover staging, no unknown records. A failed
  stage is reported as *incomplete* by name; the next `run` resumes from it.
  Exit status 1 on any incomplete or broken stage. Creates nothing.

Cancellation is cooperative: the runner checks a `CancelToken` between
stages and a stage calls `ctx.checkpoint()` at its own safe points. A stage
cancelled mid-way is recorded as `cancelled`, its staging discarded, and its
previous outputs (if any) are no longer vouched for. Nothing in the state
file is machine-specific: relative paths, digests, parameters, UTC
timestamps; error text has the data root replaced by `<data-root>`.

**Preflight** (`phillysim.preflight`) runs before every `run` and reports all
checks in one pass: free disk under the data root, physical RAM, Python
version, the locked packages (geopandas, pyogrio, shapely, pyproj, duckdb,
pyarrow), and a writable root. A real run applies the architecture.md
budgets (≥150 GB free disk, 24 GB RAM); `--fixture` applies fixture-scale
thresholds (1 GiB each) and the report says so. Any failed check refuses
the run without touching the data root.

### The fixture pipeline

`phillysim run --fixture` runs the eleven-stage fixture pipeline
(`phillysim.fixtures.pipeline`) in its own data root, `<data root>/fixture/`
(gitignored): `acquire` generates tinycity and admits each of the eight raw
snapshots through `quarantine.admit`; `validate` checks every source against
its contract; `spine`, `demographics`, `destinations`, `conflate`, `network`,
`metrics`, and `publish` compute their outputs from the raw files; `hours`
and `travel_times` are explicit **stubs** that take their answers from the
generator's oracle until M4 (hours parsing) and M3 (routing) supply the real
logic. The four curated outputs equal the committed golden tables
(`tests/fixtures/tinycity/expected/`) by content, which the integration suite
asserts. CI runs `run`, `status`, and `verify --fixture` on Windows and Linux
(the M1 go/no-go).

## The real pipeline and the download path (EP-5a)

Without `--fixture`, the verbs use the real pipeline (`phillysim.pipeline`,
name `real`) on the resolved data root. It shares the fixture pipeline's
stage names, zones, and output paths where the two overlap, so the
architecture.md stage table describes both, but the two never meet: the
state file records its pipeline's name and refuses the other one, and the
roots differ (`<data root>/` versus `<data root>/fixture/`). Nine stages
exist: `acquire` and `validate` (EP-5a), `spine` and `demographics`
(EP-5b), `snap_retailers` (EP-6; the first per-source destination layer,
which the fixture pipeline has no counterpart for), `basemap` (EP-8b; the
roads layer of the basemap, likewise real-only), `network` (EP-12; the
routing inputs, the same stage name as the fixture's with a real body), and
`metrics` and `publish` (EP-7, EP-8b).

- `acquire` brings in the pinned snapshot of each registered source
  (`phillysim.pipeline.SNAPSHOT_IDS`, one acquisition date per source since
  EP-12: `2026-09-02` for the five sources below, `2026-09-03` for the two
  routing sources): TIGER/Line 2025 tracts (`tiger_tracts`), CenPop2020
  tract centers (`cenpop`), the ACS 5-year 2020–2024 tables B01003 and
  B08201 (`acs`), the USDA SNAP Retailer Locator historical file
  (`snap_retailers`, EP-6), the TIGER/Line 2025 county roads file
  (`tiger_roads`, EP-8b), Geofabrik's dated Pennsylvania OpenStreetMap
  extract with its MD5 sidecar (`osm_network`, EP-12; ODbL, the first
  Bucket B source), and SEPTA's GTFS release asset (`gtfs`, EP-12; SHA-256
  pinned), each into `raw/<source>/<snapshot-id>/` with the archived terms
  page (for USDA, the provider's data page in force) and a manifest. A file
  whose adapter pins a digest is compared against it, and a provider
  checksum sidecar against the file it vouches for, before admission (a
  mismatch quarantines with kind `digest`); a PBF is never opened as an
  archive. A snapshot already in the raw zone is verified and re-used,
  never re-downloaded (and never replaced: a tampered one fails the stage);
  the source list and the snapshot IDs are stage parameters, so registering
  a source re-runs the stage for the new one only. It also writes
  `intermediate/acquisition.json` (URLs, bytes, attempts, timings, digests
  checked, filter placement, guard limits per source). A controlled refresh
  is a change to one source's entry in `SNAPSHOT_IDS`, recorded in the
  changelog; older snapshots stay.
- `validate` reads each snapshot through its adapter, which applies the
  Philadelphia County filter (state files are stored as delivered and
  filtered at first read; see the adapter docstrings and
  [docs/data-dictionary.md](../docs/data-dictionary.md)), and checks the
  result against the source's contract; `intermediate/validation.json`
  records rows, nulls, and violations.
- `spine` (EP-5b, `phillysim.spine`) builds the curated tract spine
  `curated/tracts_spine.parquet` (GeoParquet): TIGER geometry reprojected
  into the analysis CRS EPSG:26918 (NAD 83 / UTM zone 18N, metres;
  [ADR-0007](../roadmap/adr/0007-analysis-crs.md)), the 2020 Census
  population and the population-weighted center from CenPop (never
  recomputed from geometry), one row per tract keyed by GEOID. The stage runs
  the geospatial invariants on its own output (CRS as declared, geometry
  valid and inside the county bounds, GEOID pattern / uniqueness / count of
  408, one center per tract) and fails on any violation; `crs` and
  `expected_tracts` are its parameters.
- `demographics` (EP-5b) joins the pinned ACS estimates and margins of error
  (`B01003_001`, `B08201_002`) one-to-one to the spine into
  `intermediate/acs_tracts.parquet`, suppressed cells left null (ADR-0004),
  and checks the join cardinality the same way.
- `snap_retailers` (EP-6, `phillysim.destinations`) builds
  `curated/snap_retailers.parquet` (GeoParquet, analysis CRS): every SNAP
  retailer in the county authorized as of the file's as-of date, keyed by
  `snap_retailers:<record id>`, with USDA's store type, the project's
  format class from the packaged mapping (`phillysim.classify.store_format`,
  rendered into `docs/method-cards/store-formats.md`), a
  `supermarket_format` flag, and the tract containing the point; it enforces
  the layer's invariants on its output and writes a count report to
  `intermediate/snap_retailers.json`. Its parameters are `crs`,
  `mapping_version`, and `as_of`.
- `basemap` (EP-8b, `phillysim.basemap`) builds `curated/basemap_roads.parquet`
  (GeoParquet, analysis CRS): the county's primary and secondary roads from
  the TIGER/Line county roads file (the adapter keeps MTFCC S1100 / S1200
  at read; 426 roads, 1,044 km), the provider's geometry reprojected and
  nothing else, keyed by `linearid` with `name`, `mtfcc`, and `route_type`;
  it enforces the layer's invariants against the spine (every road touches a
  tract, none outside the county bounds) and writes
  `intermediate/basemap.json`. Its parameters are `crs` and `road_classes`.
  The county boundary needs no stage: `publish` dissolves the spine.
- `network` (EP-12, `phillysim.network`) writes the routing inputs into
  `intermediate/network/`: the OSM extract clipped with pyosmium to the
  county bounds buffered by 5 km in the analysis CRS (way-complete: every
  way touching the box with all of its nodes, the restriction relations
  among them, the source order, the box in the header; for the pinned
  extract 5.8 million nodes, 922 thousand ways, 50 MB, about three
  minutes), its contract enforced in-stage (a readable PBF carrying the
  box, counts within the recorded bands, every node inside the box or
  referenced by a kept way, `highway` ways present), and SEPTA's two feed
  zips copied out of the release asset as files through the nested zip
  guards, never expanded; `intermediate/network.json` holds the counts
  (stops outside the box are counted, not dropped) and the directory's
  license bucket, **B** by derivation. Its parameters are `buffer_m`,
  `crs`, `node_band`, and `way_band`. No JVM runs here; nothing downstream
  of it reaches `publish`, so the public zone stays Bucket A.

`phillysim run` (or `run --stage network`) needs the network once (about
490 MB: 98 MB from `www2.census.gov` and `www.census.gov`, 24 MB from
`www.fna.usda.gov`, 346 MB from `download.geofabrik.de`, 22 MB from
GitHub's release-asset host, plus the terms pages; under a minute on a
fast connection) and the real-run preflight thresholds; afterwards `run`,
`status`, and `verify` are offline, and every stage takes a few seconds
except `network` (the clip: minutes). The invariants can be re-run on a
real data root by hand:

```
uv run pytest tests/test_spine_invariants.py tests/test_basemap.py --real-data-root ../data -s
```

CI never passes `--real-data-root`; those tests skip without it and the rest
of the module runs on the committed samples.

The download path (`phillysim.download`) is the outbound side of
architecture.md's security section, in a fixed order: every URL is checked
against the adapter's domain allowlist **before any connection** (https only,
no credentials, no IP literals; redirect targets are checked too, and the
opener has no plain-http handler); each connection has a timeout and at most
three attempts per URL with bounded backoff (1 s, 2 s, 4 s, capped at 8 s)
on transient failures, a definitive failure moving straight to the alternate
URL (the manifest's dual-URL field); bytes stream through `copy_capped`
under the source's own `Limits`, so a lying `Content-Length` cannot bypass
the cap; a downloaded zip is inspected for slip and bomb conditions before
anything could be extracted (nothing is: the TIGER shapefile is read from
the zip in place); the terms page in force is fetched through the same path,
archived beside the data as `terms.html`, and checked for the sentence the
adapter expects, different wording being the stop condition (the snapshot is
quarantined with reason kind `terms` and nothing is admitted); the manifest
is built by the manifest engine; and admission goes only through
`quarantine.admit`. There is no default allowlist: each adapter declares its
domains (`www2.census.gov`, `www.census.gov` for all three spine sources).
No secret exists in the project; if a provider ever demands an API key, the
path can attach one at request time only and never records it.

Every one of those branches is exercised offline by `tests/test_download.py`
on a fake transport, and `tests/conftest.py` disables sockets for the whole
suite, so no test can reach the network by accident. The contract tests and
the real pipeline's integration tests run on the committed samples under
`tests/fixtures/spine-samples/` (real-shaped subsets of the public-domain
snapshots).

## The public zone and the publish gate (EP-7)

Both pipelines end in a `publish` stage (`phillysim.publish`) whose single
declared output is the whole `public/` directory, so the runner installs or
replaces the zone atomically and a failure leaves nothing behind. The stage
widens the analytic table onto the tracts (one column group per metric:
estimate, MOE, CV tier, reliability action, and a build-time class bin whose
edges are recorded in the manifest), writes the facility points, writes the
basemap (`basemap.geojson`, public schema version 2 since EP-8b: the county
boundary dissolved from the spine and, on the real pipeline, the curated
roads, one `layer` per feature), reprojects everything to WGS 84, escapes
CSV cells against spreadsheet formulas, labels
every file with the license bucket *derived* from its sources' manifests
(ADR-0003: Bucket B if any source is; the fixture's zone is Bucket B because
its synthetic `osm_network` is, the real slice's is Bucket A / CC BY 4.0),
and then runs the gate on the staged zone. The gate
(`phillysim.publish.gate.check_public_zone`) reads the directory as a
stranger would and refuses it on any of: a file unlisted, missing, or
altered; a label that differs from the derived bucket or from the in-file
label; a Bucket B file without the ODbL and OpenStreetMap notices; a
coordinate outside WGS 84 or the declared bounds, or a `crs` member; an
unescaped CSV cell; a pipeline path, state file, or absolute path mentioned
anywhere (the manifest included); a column name that is not a slug or
carries a term the claims matrix prohibits; a `qa_` column not declared
QA-only; or two formats of one table that disagree. Columns, files, and the
manifest are documented in [docs/data-dictionary.md](../docs/data-dictionary.md)
("Public zone", public schema version 1, a `publish` stage parameter).

```
uv run phillysim run                 # ... metrics, publish (gated before install)
uv run phillysim gate                # re-check the installed public zone; exit 1 on any violation
uv run phillysim gate --fixture      # the CI step
uv run phillysim gate --public DIR   # any directory claiming to be a public zone
```

The real pipeline's `metrics` stage today computes one deliberately trivial,
**QA-only** number per tract (`phillysim.metrics.slice`: straight-line
distance to the nearest supermarket-format SNAP retailer, metric ID
`qa_straight_line_m`) to prove that path; it is not an access measure and
the gate enforces the flag that says so
([method card](../docs/method-cards/qa-straight-line.md)). Nothing under any
`public/` zone is committed or deployed.

## The slice page (EP-8a, EP-8b)

The repository root's [`site/`](../site/README.md) holds the page sources
(vanilla ES module + vendored MapLibre GL JS) and `phillysim site build`
turns a **gated** public zone into a static site under `site/dist/`
(gitignored): the gate is re-run, the six public files are copied byte for
byte (the basemap, county boundary plus TIGER major roads, is one of them
since EP-8b; nothing is derived at build time), and `site.json` records
every digest; the build is deterministic. `phillysim site serve` serves it
on loopback. The page reads `manifest.json` for everything it shows
(columns, descriptions, bin edges, the QA note, sources and snapshot IDs,
license and attribution, the basemap's layer counts) and makes no request
to any other host; the roads are drawn in a gray whose contrast ratios are
measured by a test and tabulated in the site README. It is labeled work in
progress and is not deployed (roadmap open question OQ-H).

```
uv run phillysim site build --fixture    # from data/fixture/public/
uv run phillysim site build              # from data/public/ (the real slice)
uv run phillysim site serve              # http://127.0.0.1:8000/
```

`tests/test_site_browser.py` drives the fixture-built page through
Playwright in the machine's own Chrome or Edge (Playwright's `channel`
option: nothing is downloaded) and asserts the map and tables render
offline, zero axe-core violations, the keyboard order, 320 px reflow,
reduced motion, and the no-WebGL fallback; CI runs it on both platforms and
fails, rather than skips, if no browser can be launched.

## The routing toolchain and harness (EP-13)

The M3 routing spike runs r5py on a JVM the project controls
([ADR-0008](../roadmap/adr/0008-routing-toolchain-pins.md)): Eclipse
Temurin JDK **21.0.12.1+1** and the R5 jar, both downloaded once through the
guarded download path (allowlist `github.com` plus GitHub's two release-asset
hosts, https only, capped streaming), compared against the recorded byte
counts and SHA-256 digests **before** anything is installed (a mismatch
deletes the download and stops), and installed **project-local**:

```
uv sync --locked --group routing      # r5py 1.1.7, JPype1 1.7.1, psutil 7.2.2 (wheels)
uv run phillysim toolchain install    # .jdk/jdk-21.0.12.1+1/ and .r5/<jar>, about 270 MB once
uv run phillysim toolchain check      # java -version, the jar's digest, the record, the group
```

The JDK archive is the one archive the project extracts; it goes through the
zip-slip and bomb guards (`guards.extract_zip`, or `guards.extract_tar` for
the Linux tarball, whose in-root symlinks are allowed and whose escaping ones
are refused) into a scratch directory, and the JDK moves into place only
after its own `java -version` reports `21.0.12.1`. Nothing lands on `PATH`,
in the registry, or in the system; `.jdk/`, `.r5/`, `*.jar`, and the
`toolchain.json` record are gitignored and a test asserts none is tracked.
`JAVA_HOME` is set in the routing child's environment per invocation and
nowhere else.

The `routing` dependency group is optional: `uv sync --locked` (what CI
runs) does not install it, and no module under `phillysim` imports r5py or
JPype at module level (importing r5py starts the JVM and, without a jar,
downloads one); only the harness child imports r5py, inside the function
that runs in the child (`tests/test_no_jvm_in_ci.py`). `psutil` is a core
dependency because the sampler and the CI performance-smoke test use it.

**Every JVM run is a child process** (`python -m phillysim.routing.harness
<run dir>`), never the CLI process, with an environment built per
invocation: `JAVA_HOME` = the project-local JDK; `JAVA_TOOL_OPTIONS=
-XX:ActiveProcessorCount=8` (architecture.md's parallelism cap); r5py's
arguments through its own `configargparse` parser on the child's `sys.argv`
(`--max-memory 12G`, `--r5-classpath <the installed jar>`, so r5py's own
download path is never exercised, and `--temporary-directory` under the
data root); and r5py's cache under the data root (`cache/r5py/`: r5py reads
`LOCALAPPDATA` on Windows and `XDG_CACHE_HOME` on Linux, so the child's
environment sets both; it copies its inputs there as working copies, builds
the network there as `<digest>.mapdb` and `<digest>.transport_network`, and
expires cache files older than two weeks; `APPDATA` / `XDG_CONFIG_HOME` point
under the same directory so no user-level `r5py.yml` is read or written).
`PATH` is untouched. The child's stdout and stderr go to the run's
`log.txt`.

A thread in the parent samples the child **and all its descendants** with
psutil at >= 1 Hz (1 Hz, 4 Hz during the first minute), records the peak sum
of RSS and the whole series, notes the second the **20 GB** budget line is
first crossed, and kills the tree (children first) the moment a sample
reaches **22 GB** (architecture.md "Resource budgets"). Wall time runs from
the child's start to its exit. Each run leaves
`<data root>/runs/routing/<UTC timestamp>-<slug>/` with `plan.json`,
`record.json` (outcome `completed` / `killed-rss` / `failed` / `cancelled`,
wall, peak RSS and when, the budget crossing, the toolchain digests, the
inputs' digests, the output's byte digest and canonicalized-value digest),
`rss.csv`, `log.txt`, `child.json`, `phases.json`, and `travel_times.csv`;
the shape is in [docs/data-dictionary.md](../docs/data-dictionary.md). Every
path inside is data-root-relative and the data root, the repository root,
and the project directory are scrubbed to placeholders.

```
uv run phillysim route smoke                       # three runs, walk and walk+transit
uv run phillysim route smoke --single-departure    # a one-minute window (EP-15's hand check)
```

`route smoke` runs the real-run preflight plus the toolchain check, then
routes from the spine center of the tract containing City Hall
(`42101000500`) to the supermarket-format retailer nearest to it, walk at
4.8 km/h and walk+transit at 4.8 km/h on the pinned Wednesday
(2026-09-23) from 08:00 with a 60-minute window, percentiles 50 and 85,
`max_time` 120 minutes, on the `network` stage's clipped extract and the two
SEPTA feed zips; three times in a row, each run its own record; then reports
whether the three canonicalized-value digests agree (the first determinism
observation) and the peak RSS against the 22 GB line. r5py's default walking
speed is 3.6 km/h and is overridden on every call.

## Resource baselines

Recorded at the EP-9 checkpoint (2026-09-02) from a fresh clone of `main`
at `a72d318` on the development machine (Windows 11), as the reference for
later checkpoints. Every number is trivially within the architecture.md
budgets at fixture scale.

| Measure | Baseline | Budget (architecture.md) |
|---|---|---|
| `git clone` | about 2 s | — |
| `uv sync --locked` | about 6 s with a warm uv cache; `.venv` 363 MB | — |
| `uv run pytest` (240 tests) | about 10 s | — |
| `phillysim run --fixture`, first run | 1.5 s wall including preflight; `acquire` and `validate` about 0.1 s each, every other stage under 0.05 s | routine peak RAM ≤24 GB (not measured yet) |
| second run (0 ran, 11 skipped) | about 1.0 s | — |
| `status --fixture`, `verify --fixture` | under 1 s each | — |
| fixture data root after a run | 148 KB (raw 55 KB, curated 44 KB, intermediate 29 KB, state file 12 KB, public 4 KB) | workspace ≤50 GB |
| preflight report | 429 GB free disk, 68.1 GB physical RAM, Python 3.13.15, all six locked packages present | real run needs ≥150 GB free and 24 GB RAM (would pass on this machine) |

Peak RSS is not measured yet: process-tree RSS sampling starts with the M3
spike harness, which is also where the CI performance-smoke test in
[roadmap/quality.md](../roadmap/quality.md) lands.

First real run (EP-5a, 2026-09-02, same machine): `phillysim run --stage
validate` downloaded 13.1 MB (TIGER zip, 0.5 s), 145 KB (CenPop, 0.2 s),
18.3 MB + 65.0 MB (the two ACS tables, 0.6 s + 1.3 s) and three copies of
the 311 KB terms page (0.5 s each); `validate` read all three sources (408
tracts each) in 1.1 s; the run took about 4 s wall including preflight. The
raw zone holds 94 MB. A repeat run skips both stages in about 1 s;
`status` and `verify` take about 1 s each.

First slice through the publication boundary (EP-7, 2026-09-02, same
machine): on the existing data root `phillysim run` skipped the five fresh
stages and ran `metrics` in 0.1 s and `publish` in 0.3–0.4 s (408 tracts,
164 supermarket-format points, the gate included); the public zone is
965 KB (`tracts.geojson` 876 KB, 176 KB gzipped; `sites.geojson` 45 KB;
the two CSVs 38 KB; `manifest.json` 6 KB), well under the "sub-MB gzipped"
size architecture.md sizes the site's payload at; the data root is 118 MB.
`phillysim gate` on the real zone takes about 1 s. The test suite is
400 tests in about 15 s (the fixture pipeline is built several times).

The basemap roads (EP-8b, 2026-09-03 UTC, same machine): on the existing
data root `phillysim run` re-ran `acquire` (7.2 s, the roads zip 1.35 MB in
0.3 s plus its terms page, the four other snapshots re-used), `validate`
(3.3 s), `spine` and `snap_retailers` (their `validation.json` input
changed; byte-identical outputs), `basemap` (0.3 s), and `publish` (0.6 s;
the schema bump made it stale on parameters); about 15 s wall. The raw zone
gains 1.7 MB (data root 120 MB); `curated/basemap_roads.parquet` is 272 KB;
`public/basemap.geojson` is 589 KB (140 KB gzipped), so the whole zone is
1.5 MB (about 330 KB gzipped) and the built site 2.8 MB. The suite grows
to 461 tests in about 30 s, the sample-built real zone and its browser run
included.

**EP-10 checkpoint (2026-09-03, same machine): the whole real pipeline
from a fresh clone of `main` at `deb21fc`, cold caches, empty data root.**
This is the reference for later checkpoints; every number is within the
architecture.md budgets, and every provider data file, curated table, and
public file came back byte-identical to the working clone's (the
refresh-drift check: the five providers still serve the pinned bytes).

| Measure | Baseline | Budget (architecture.md) |
|---|---|---|
| `git clone -c core.longpaths=true` | 1.4 s; `.git` 4.6 MB | — |
| `uv sync --locked` | 9 s (cold); `.venv` 477 MB | — |
| `uv run pytest` (461 passed, 3 skipped) | 47 s cold (30 s warm in the working clone) | — |
| fixture verbs | `run --fixture` 1.6 s (11 ran), 1.0 s (0 ran, 11 skipped); `status` 0.9 s; `verify` 0.9 s (8 of 8 snapshots, 11 of 11 stages); `gate` 0.8 s (5 files Bucket B); `site build` 1.2 s | — |
| `phillysim run`, real, from empty | 15.1 s wall: `acquire` 7.0 s, `validate` 3.0 s, `spine` 0.2 s, `demographics` 0.8 s, `snap_retailers` 2.3 s, `basemap` 0.3 s, `metrics` 0.0 s, `publish` 0.5 s (8 ran) | unattended runs are M3's; routine peak RAM ≤ 24 GB (not measured: peak RSS is deferred to the M3 spike harness by owner decision) |
| fresh acquisition, per source (data files; each terms page 311,057 B in 0.5 s, the SNAP data page 44,082 B in 0.3 s; every fetch one attempt) | ACS 18,313,708 B in 0.6 s + 65,043,091 B in 1.3 s; CenPop 144,662 B in 0.2 s; SNAP 24,036,753 B in 1.2 s; roads 1,352,071 B in 0.3 s; tracts 13,109,450 B in 0.5 s; 123.3 MB in all | network: the same five files as EP-8b (about 122 MB); guard `Limits` per source held |
| second `run` (0 ran, 8 skipped) | 1.1 s | — |
| `status`, `verify` (5 of 5 snapshots, 8 of 8 stages), `gate` (5 files Bucket A, 4 sources), `site build` (`county_boundary (1), roads (426)`) | 1.1 s, 1.0 s, 1.0 s, 1.4 s | — |
| `pytest --real-data-root` (spine, basemap, slice, destinations invariants) | 57 passed in 1.9 s | — |
| real data root | 125.9 MB: raw 123.3 MB, public 1.56 MB, curated 891 KB, intermediate 22 KB, state file 8 KB, cache and quarantine empty | workspace ≤ 50 GB |
| public zone | 1,555,668 B raw, 331,050 B gzipped (`tracts.geojson` 875,603 B / 174,979 B gz; `basemap.geojson` 588,768 B / 139,141 B gz; `sites.geojson` 44,931 B; the two CSVs 38 KB; `manifest.json` 8 KB) | sub-MB gzipped site payload |
| built site (`site/dist/`) | 2.77 MB (the zone plus the page and the vendored MapLibre) | — |
| fresh clone in all (checkout, `.venv`, data root, built site) | 620 MB, deleted afterwards | EP-10 budget: about 0.6 GB |
| CI (run 33795124091 on `deb21fc`) | ubuntu job 49 s (`uv sync` 3 s, pytest 32 s); windows job 96 s (`uv sync` 12 s, pytest 54 s); `run --fixture` about 1 s on both | — |
| preflight report (real thresholds) | 422.9 GB free disk (need ≥ 150 GB), 68.1 GB physical RAM (need ≥ 25.8 GB), Python 3.13.15, geopandas 1.1.4 / pyogrio 0.13.0 / shapely 2.1.2 / pyproj 3.7.2 / duckdb 1.5.5 / pyarrow 25.0.1, root writable | ≥ 150 GB free, 24 GB RAM |

The routing sources (EP-12, 2026-09-03, same machine): on the existing data
root `phillysim run --stage acquire` fetched the Geofabrik extract
(345,912,530 B in 15.5 s, one attempt) with its 62-byte MD5 sidecar and
the region page (23 KB), and SEPTA's release asset (21,555,258 B in 0.8 s,
one attempt) with its developer page (18 KB), the five other snapshots
verified and re-used; 20 s in all. `run --stage network` then re-ran
`validate` (4.4 s for seven sources; the OSM read is header-only) and the
`network` stage in 182 s: three streaming passes over 45.1 million nodes,
4.9 million ways, and 55.8 thousand relations, the clip written with the
ID filter (5.8 million nodes, 922 thousand ways, 3.7 thousand relations,
49,968,756 B), its contract checked, and the two feed zips unwrapped
(20.8 MB and 0.76 MB). The raw zone grows by 367 MB (data root about 560
MB with the 71 MB `intermediate/network/`); `osmium` adds 6 MB to `.venv`.
Peak RSS of the clip was not measured at EP-12; the clip's Python sets
hold about 6 million node IDs and 0.9 million way IDs.

**The routing toolchain and the first JVM runs (EP-13, 2026-09-03, same
machine).** `uv sync --locked --group routing` added 18 packages
(`.venv` 480 MB to 738 MB; scipy, rasterio, and scikit-learn are the
bulk). `phillysim toolchain install`: the JDK zip 205,073,461 B in 14.8 s
(digest equal to ADR-0008's, 490 archive members extracted under the
guards, `.jdk/` 329 MB) and, after the ADR-0008 jar amendment, the jar
`r5-v7.5.1-r5py-all.jar` 64,437,972 B in 1.5 s (digest equal to the
amended pin, `.r5/` 62 MB); the pre-amendment jar (65,104,016 B in 4.8 s,
digest equal to the gate's pin) had installed and verified the same way
before r5py refused it. The process-tree RSS sampler exists since this
packet and every number below is its peak sum of RSS over the child and
its descendants.

| Measure | Baseline | Budget (architecture.md) |
|---|---|---|
| CI performance smoke: `phillysim run --fixture` as a child under the sampler | 1.3 s wall, peak RSS 140 MiB, 10 samples at 10 Hz (Windows; the Linux numbers are in the CI log) | 60 s / 2 GiB test bounds |
| `phillysim route smoke` on the jar ADR-0008 pinned **before its amendment** (`r5-v7.6-r5py-all.jar`) | 1 run, `failed` at 8.5 s: r5py 1.1.7 cannot construct `com.conveyal.osmlib.OSM` from this jar (its constructor is private in R5 7.6); peak RSS 0.33 GB; the JVM itself started from the project-local JDK with the pinned classpath | the packet's stop condition; ADR-0008 amendment with the owner |
| **`phillysim route smoke` on the pinned toolchain** (after the amendment: `r5-v7.5.1-r5py-all.jar`), three runs, records under `data/runs/routing/` | cold: 45.1 s wall, **peak RSS 4.94 GB** at 37 s (r5py import 1 s; network build 43 s at 4.94 GB; each route under a second at 4.72 GB); with r5py's cached network: 6.2 s and 6.2 s wall, peak RSS 2.52 GB and 2.43 GB (build from cache 2 s); the three canonicalized-value digests equal (`cab6893e…`) and the three byte digests equal (`02987354…`); walk 4 min and walk+transit 4 min (p50 = p85) for the 240 m pair; `--single-departure` (a one-minute window): 5.8 s, 2.43 GB, the same values | 20 GB budget, 22 GB kill: well under; **the first peak-RSS number of the project** |
| Diagnostic smoke on the same jar before the amendment (a scratch toolchain home, records under `data/runs/routing-diagnostic/`) | cold: 45.3 s wall, **peak RSS 4.81 GB** at 37 s (r5py import 3 s, network build 40 s at 4.81 GB, walk route 1 s, walk+transit route under 1 s); with r5py's cached network: 8.0 / 6.3 / 6.4 s wall, peak RSS 2.36 / 2.45 / 2.54 GB (build 2–3 s); all four completed runs' canonicalized-value digests equal (`cab6893e…`), byte digests equal (`02987354…`); walk 4 min and walk+transit 4 min (p50 = p85) for the 240 m pair | 20 GB budget, 22 GB kill: well under; the first peak-RSS number of the project |
| r5py's network cache (`data/cache/r5py/`) | `<digest>.transport_network` 416 MB, `.mapdb.p` 106 MB, `.mapdb` 4 MB; the three inputs linked, not copied (symlinks on this machine); about 0.9 GB with the temporary directories the killed and failed children left under `tmp/`; r5py expires files older than two weeks | workspace ≤ 50 GB |
| run records | about 12 KB per run (`rss.csv` dominates: 160 rows for the cold run) | — |
| test suite | 583 passed, 3 skipped in about 44 s (516 before the packet) | — |

## Decisions this package honors

- [ADR-0001](../roadmap/adr/0001-language-and-stack.md): Python 3.12+/uv on
  native Windows; pyogrio-only geo I/O; `GDAL` and `fiona` PyPI packages banned
  and tested for.
- [ADR-0002](../roadmap/adr/0002-storage-geoparquet-duckdb.md): GeoParquet
  zone files + DuckDB spatial; no PostGIS.
- Locked-stack packages (geopandas, pyogrio, shapely, pyproj, duckdb, pyarrow)
  are declared now so the ban test and the Windows-wheel requirement are
  exercised from the first commit; since EP-13 r5py, JPype1, and psutil form
  the optional `routing` group (wheels on Windows and Linux) and the pinned
  JDK and R5 jar are installed project-local by `phillysim toolchain install`.
- [ADR-0008](../roadmap/adr/0008-routing-toolchain-pins.md): the exact JDK
  build, the jar, the heap, the processor cap, the cache under the data root,
  the calendar, and the spike's decision numbers; `JAVA_HOME` per invocation.
