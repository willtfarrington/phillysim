# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
the axes in [roadmap/quality.md](roadmap/quality.md) (ADR-0006) — code is
SemVer 0.x pre-v1, and data snapshots, schema, and method versions are
recorded separately in manifests once the pipeline exists.

## [Unreleased]

### Changed

- **EP-10 — checkpoint 2** (after M2, before the M3 refinement gate;
  2026-09-03). Fresh clone of `main` at `deb21fc` re-run green, fixture
  and real: `uv sync --locked`, 461 tests; `phillysim run --fixture` (11
  ran, then 0 ran / 11 skipped), `status` (11 fresh), `verify` (8 of 8
  snapshots, 11 of 11 stages), `gate` (Bucket B), `site build`; then the
  real pipeline from an empty data root with a **fresh acquisition of all
  five providers** (123 MB, every fetch one attempt): 8 stages in 15 s,
  then 0 ran / 8 skipped, `status` 8 fresh, `verify` 5 of 5 and 8 of 8,
  `gate` green (5 files Bucket A, 4 sources), `site build` with
  `county_boundary (1), roads (426)`. **Every provider data file, curated
  table, and public file is byte-identical to the recorded references**
  (the refresh-drift check: no controlled refresh is due; the archived
  terms pages differ per fetch as recorded since EP-5a and still carry
  the checked sentences). License sweep on the real zone clean: every
  file's bucket equals the bucket derived from its sources' manifests,
  the attribution lines equal the adapters' citations and the
  DATA-LICENSES records, the `license_note` texts equal the manifests',
  the in-file labels equal the manifest's, nothing under any `public/`
  zone or `site/dist/` is tracked. Documentation synced to the code:
  `roadmap/quality.md` (five real sources under contract, the real
  pipeline's eight stages in the integration row), `roadmap/architecture.md`
  (the `acquire` row names all five sources), `docs/DATA-LICENSES.md`
  (the labeling status names the roads snapshot and records the trace),
  `docs/data-dictionary.md` (the contract note), the root README's
  dictionary line. Resource baselines for the real pipeline from a fresh
  clone appended to `phillysim/README.md` (peak RSS still deferred to the
  M3 spike). Dependency triage: no open Dependabot PR, no open alert (the
  eight alerts are the dismissed vendored-tree ones), `uv lock --check`
  clean, MapLibre 6.7.0 and the SHA-pinned actions noted. `milestones.md`
  "Estimate accuracy" gains EP-5a through EP-9 and the M2 roll-up (6 of
  4–6: every packet one session, the split M packets two each), a new
  implication note (plan against the high bounds; the gate's packet count
  replaces the range), the re-plan trigger evaluation (none fired), and
  the re-sizing proposal put to the owner. M3 gate pre-read recorded in
  the EP-10 handoff (inputs, eight questions, the gaps in the planning
  documents: no JDK / R5 pin values, no determinism band or hand-check
  tolerance, no routing-source adapters, one `SNAPSHOT_ID` for all
  sources).

### Added

- **EP-15 — the M3 verdict: criteria against the records, the determinism
  band, the hand check, the walk concordance, the `travel_times` stage**
  (M3; 2026-09-03 and 2026-09-04; work commit `7202f43`, the scipy-free
  Spearman fix `9638bd2`, CI run 33828405482 green; **closed 2026-09-04:
  the hand check 34 of 40, the outcome code go, M3 closed, the second
  night run and verified, the third checkpoint authored as EP-16**).
  `phillysim route verdict --night ID [--json] [--write] [--record CODE]`
  (`phillysim.routing.verdict`) reads a finished or killed night against
  every criterion of milestones.md, methodology.md, architecture.md, and
  ADR-0008, each with its source quoted, its number, and a status: the core
  wall against 8 h, the peak process-tree RSS against the 20 GB budget and
  the 22 GB kill (a peak between them is a pass with a finding), each core
  run against its repeat **pair by pair** in integer minutes on both time
  columns against the band (identical, or ≥ 99.9 % identical with no
  difference over 1 min), each core run's finite pairs against 95 % (the
  walk run also against the straight-line reach bound the censor allows at
  all, because its reading is the owner's), the hand check's tally against
  32 of 40, the concordance against ρ ≥ 0.95; it suggests, and `--record`
  writes the code the owner confirmed into `verdict.json` beside the
  measurements. `phillysim route handcheck --night ID [--skip GEOID]`
  (`phillysim.routing.handcheck`) selects the ten pairs by rule (every
  fortieth tract by GEOID from the first, the nearest supermarket-format
  retailer by the QA slice's rule; the fifth and tenth the farthest one
  under the censor by the core walk run; a skipped tract substituted by the
  next in sorted order), routes them in single-departure mode at 08:30 and
  17:30 on the pinned Wednesday for walk and walk+transit (two harness runs
  under `<night>/handcheck/`), prints the forty project-side times with both
  points' coordinates, and, with `--planner FILE` or `--tally`, tallies a
  **hand-typed** `planner.csv` against the tolerance (walk 3 min or 15 %,
  walk+transit 10 min or 25 %, the larger) and the gate; nothing reaches a
  planner. `phillysim route concordance --night ID` (`phillysim.routing.concordance`)
  builds methodology.md's fallback engine on the night's clip with no
  network call (the walkable ways selected with pyosmium by OSMnx's own
  `walk` filter rules, written as OSM XML under `cache/concordance/`, read
  with `graph_from_xml`, Overpass and Nominatim disabled), walks the 408 ×
  164 supermarket-format pairs with scipy's sparse Dijkstra at 4.8 km/h,
  and reports Spearman ρ against the core walk run over the pairs both
  engines report under the censor, with every exclusion counted. `osmnx
  2.1.1` and `scipy 1.18.1` join the optional `routing` group (ADR-0008);
  CI installs none of it, so the OSMnx-side tests skip there. **The
  `travel_times` stage** (`phillysim.routing.stage`, registered between
  `network` and `metrics`; ten real stages): the two core runs as the
  tracked plan `travel-times.json` (the spike's core runs verbatim), routed
  as a night under the EP-14 driver, concatenated into
  `curated/travel_times.parquet` in the dictionary's shape (1,312,944 rows,
  Bucket B by derivation, never read by `publish`) with
  `intermediate/travel_times.json`; the plan's digest and parameters are the
  stage's parameters; a finished night on the same plan, points, and inputs
  is re-used, a stopped one resumed; the stage refuses without the routing
  group and the toolchain and names the install. **The evidence** (night
  `20260903T223607Z-m3-spike`): core wall 830 s of 8 h; peak RSS 5.39 GB;
  both core runs identical to their repeats pair for pair (656,472 of
  656,472 each; OQ-C closed with a zero band; quality.md's wording
  confirmed); walk+transit 99.95 % finite; walk 46.95 % against a reach
  bound of 56.24 % (the owner's reading); concordance ρ = 0.9935 over
  28,256 pairs (graph 265,006 nodes, 748,296 edges; 2.3 min; peak RSS
  5.46 GB); forty hand-check times routed (10 s per run, 4.4 GB) and, on
  2026-09-04, compared by hand against SEPTA's planner and a general
  planner: **34 of 40** within tolerance (walk 14 of 20, walk+transit 20
  of 20; the six misses walk checks 5 to 8 minutes under the planner on
  short trips, a finding for the M5 method card). **Outcome code go**,
  confirmed by the owner and recorded in the night's `verdict.json`;
  **M3 closed**. **The second unattended night** (`phillysim run --stage
  travel_times` detached, night `20260904T191646Z-travel-times`): finished 19:31Z after 15 min: `walk-48-wed` 80.8 s (first night 54.2 s), `transit-48-wed` 804.8 s (first night 775.7 s); core wall 885.6 s = 0.25 h of 8 h; peak process-tree RSS 5.26 GB (walk 5.26 GB, transit 3.32 GB) against the 20 GB budget; 656,472 rows per run; finite pairs walk 46.95%, walk+transit 99.95%; both runs' canonicalized-value digests **equal to the first night's** (`100625cd…` walk, `e35b466d…` transit), byte digests equal too; `curated/travel_times.parquet`
  (1,312,944 rows) with `intermediate/travel_times.json`; `phillysim status`
  ten stages fresh. `roadmap/EP-16-checkpoint-3.md` authored (the third
  checkpoint, whose fresh-clone re-run includes the routing night and
  whose pre-read authors the M4 gate as EP-17). **Fixed after the close:**
  an implicit night ID (`route matrix` and the stage without `--night`)
  is one second coarse, and a night started within a second of another on
  the same plan took its ID and was treated as a resume of it, silently,
  with the earlier night's inputs (CI run 33911808003 on the closing
  commit, Linux only: the stage's own test started two nights in one
  second); `matrix.fresh_night_id` now advances the stamp until no
  directory holds it, an explicit `--night ID` still resumes in place.
  Tests:
  `test_verdict.py`, `test_handcheck.py`, `test_concordance.py`,
  `test_travel_times_stage.py` (crafted records and scripted children, no
  JVM; the sample pipeline runs the stage on a scripted child too).
  Documentation: `docs/method-cards/travel-times.md` (stub), the data
  dictionary (the curated matrix, the stage's report, the night's verdict,
  hand-check, and concordance files), architecture.md stage 9,
  open-questions.md (OQ-C), quality.md, ADR-0008 (the band as measured),
  DATA-LICENSES, milestones.md, `phillysim/README.md`.
- **EP-14 — the pre-scripted run matrix and the first unattended night**
  (M3; 2026-09-03). The spike's runs are data before they run:
  `phillysim/src/phillysim/routing/plans/m3-spike.json` (tracked;
  `phillysim.routing.plan`) names the seven runs of the EP-14 brief with
  ADR-0008's parameters verbatim and no path — origins the 408 spine centers,
  destinations all 1,609 SNAP retailers, percentiles 50 and 85, `max_time`
  120, `snap_to_network` on; the two core runs first (`walk-48-wed`,
  `transit-48-wed`: 4.8 km/h, the Wednesday 2026-09-23 08:00–20:00 window at
  one departure per minute), their determinism repeats, the 3.0 km/h
  sensitivity pair, and the Saturday 2026-09-26 window; the ≤ 8 h wall
  criterion on the two core runs together (`core_wall_limit_hours`). The
  loader refuses a repeat whose parameters differ from its original, core runs
  not listed first, an unknown mode or table, a date outside the plan's dates.
  `phillysim route matrix --plan FILE [--only RUN] [--origins-subset N]
  [--night ID] [--continue-after-kill] [--keep-awake]`
  (`phillysim.routing.matrix`) executes the plan in order as a **night**
  under `<data root>/runs/routing/<night-id>/`: the origins and destinations
  built once (`points.parquet`), `feed_info.txt` read from both feed zips and
  the plan refused when its transit dates fall outside either authoritative
  window, r5py's cache touched, one EP-13 child per run under the sampler,
  each completed run's output turned into `travel_times.parquet` in the data
  dictionary's shape (censored at 120; the full grid) with its byte and
  canonicalized-value digests and sanity counts (share of finite pairs
  against the 95 % gate, pairs at the censor, a distribution summary) in
  `matrix.json`, and `night.json` (per-run outcome, wall, peak RSS; the core
  wall; the peak RSS over the night; the state; the outcome code; the
  driver's invocations and interruptions). A run already `completed` is
  skipped on re-invocation; a failed, cancelled, or interrupted run is re-run
  with the earlier attempt kept as `<run>.attempt<N>/`. A core run killed at
  the 22 GB line, or a core wall over the limit, marks the night
  **`KILLED-BY-EVIDENCE`** and stops unless `--continue-after-kill` (the
  owner's flag; the killed run is never re-run); a killed non-core run is
  recorded and the night goes on. `phillysim route status [--night ID]
  [--json]` reads a night back (state, driver alive or not, per run its
  status, wall so far, peak, the last RSS sample). `--origins-subset N`
  routes the plan's `rehearsal_origins` (the six CI sample tracts) first
  and the night record carries `expected_wall`, the full night extrapolated
  linearly in origins. The harness plan gains `snap_to_network` and
  `harness.run` a `run_dir` override. Tests: `test_routing_plan.py` (the
  plan against ADR-0008; the loader's rules; the points; the feed windows),
  `test_matrix_driver.py` (the driver on scripted children, no JVM: records,
  the matrix shape and sanity counts, resume, kills and the outcome code, the
  extrapolation, status, the CLI). Documentation: `phillysim/README.md`
  (the verb, the plan, how to launch and resume a night),
  `docs/data-dictionary.md` (the night record; the matrix's `mode` values
  and where the speed and window live). **The rehearsal** (`--origins-subset
  6`, the six CI sample tracts × 1,609 retailers, 2026-09-03): all seven runs
  completed in 86 s of wall together (walk runs about 7 s, transit runs at
  720 departures 15–17 s), core wall 24.4 s, peak RSS 3.53 GB, both repeats
  byte- and value-identical to their originals, every transit run 100 %
  finite pairs, the walk runs 64 % (4.8 km/h) and 35 % (3.0 km/h) under the
  120-min censor; the core wall extrapolated linearly to 408 origins is 960 s
  (0.27 h), all seven runs 0.97 h. The rehearsal's cache touch followed
  r5py's symlinks into `intermediate/network/` and refreshed three files'
  modification times (contents unchanged; every stage still fresh); the
  driver now skips symlinks. The launch of the first unattended night and
  the owner's decisions are in the packet's handoff
  (`roadmap/EP-14-routing-run-matrix.md`).
- **EP-13 — routing toolchain and harness** (M3; 2026-09-03; the project's
  first JVM runs; ADR-0008's jar pin amended with the owner, see below).
  `phillysim toolchain install` / `check`
  (`phillysim.routing.toolchain`): Eclipse Temurin JDK 21.0.12.1+1 and the
  R5 jar of ADR-0008 downloaded once through the guarded download path
  (allowlist `github.com` plus GitHub's two release-asset hosts), compared
  against the recorded byte counts and SHA-256 digests before anything is
  installed (a mismatch deletes the download), the JDK archive extracted
  under the zip-slip and bomb guards (`guards.extract_zip`; a new
  `guards.extract_tar` for the Linux tarball allows in-root symlinks and
  refuses escaping ones, hard links, and devices) into a scratch directory
  and moved into place only after its own `java -version` reports
  `21.0.12.1`; project-local under `phillysim/.jdk/` and `phillysim/.r5/`,
  recorded in `phillysim/toolchain.json`, all gitignored, nothing on
  `PATH`. The `routing` dependency group (`r5py==1.1.7`, `jpype1==1.7.1`,
  `psutil==7.2.2`; wheels on Windows and Linux for Python 3.13) is optional
  and never installed in CI; `psutil` joins the core dependencies and the
  preflight's locked packages. `phillysim.routing.harness` runs every JVM in
  a child process with a per-invocation environment (`JAVA_HOME`,
  `JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=8`, r5py's `--max-memory 12G`
  / `--r5-classpath` / `--temporary-directory` on the child's `sys.argv`,
  r5py's cache and config under `<data root>/cache/r5py/`; `PATH`
  untouched), refuses to import r5py unless the installed jar exists and
  refuses to route unless r5py resolved that jar (r5py falls back to its own
  download otherwise). `phillysim.routing.sampler` samples the process-tree
  RSS with psutil at 1 Hz (4 Hz during start-up), records the peak and the
  series, the 20 GB budget crossing, and kills the tree (children first) at
  22 GB. `phillysim.routing.records`: run plans and the scrubbed run record
  under `<data root>/runs/routing/<UTC timestamp>-<slug>/` (`plan.json`,
  `record.json`, `rss.csv`, `log.txt`, `child.json`, `phases.json`,
  `travel_times.csv`; byte digest and canonicalized-value digest of the
  output; the shape in `docs/data-dictionary.md`). `phillysim route smoke`
  (`phillysim.routing.smoke`): the spine center of the City Hall tract
  (`42101000500`) to the nearest supermarket-format retailer, walk and
  walk+transit at 4.8 km/h on the pinned Wednesday 2026-09-23 from 08:00,
  60-minute window, percentiles 50 and 85, `max_time` 120 min, three runs,
  the digests compared; `--single-departure` for EP-15's hand check. The
  routing verbs add the toolchain report to the real-run preflight. CI
  performance smoke (`tests/test_performance_smoke.py`): `phillysim run
  --fixture` as a child under the same sampler, wall under 60 s and peak
  RSS under 2 GiB asserted, the numbers in the test log (Windows: 1.3 s,
  140 MiB); the quality.md row flips to "yes". Tests: `test_toolchain.py`
  (crafted archives and digests, no network), `test_sampler.py`,
  `test_records.py`, `test_routing_harness.py`, `test_no_jvm_in_ci.py`
  (no module-level r5py or JPype import anywhere under `phillysim`, the
  child the only importer, the group not a default, CI installs none of
  it, the ignore rules, nothing tracked). **ADR-0008 amended (owner
  decision):** the smoke's first run met the packet's stop condition,
  because r5py 1.1.7 cannot build a network on the jar the gate had
  recorded, `r5-v7.6-r5py-all.jar` (R5 7.6's `com.conveyal.osmlib.OSM`
  has only a private constructor; r5py 1.1.7 calls the public one and
  pins `r5-v7.5.1-r5py-all.jar` in its own source; only r5py's
  unreleased `main` pins v7.6). The jar pin is now `r5-v7.5.1-r5py-all.jar`
  (release `v7.5.1-r5py`, 2026-05-08; 64,437,972 B; SHA-256
  `d50be106…9be7`), every other pin unchanged; the failed run's record is
  kept, and a diagnostic's records on the same jar sit under
  `data/runs/routing-diagnostic/`. **The smoke on the pinned toolchain:**
  three runs `completed`; cold network build 43 s with **peak process-tree
  RSS 4.94 GB** (the project's first), then 6.2 s and 2.4–2.5 GB with
  r5py's cached network; the three canonicalized-value digests and byte
  digests identical (the first determinism observation, OQ-C); walk and
  walk+transit both 4 minutes for the 240 m pair; the single-departure
  mode runs too. Suite 583 passed, 3 skipped.

- **EP-12 — routing sources: the OSM extract (Geofabrik, Bucket B) and
  SEPTA GTFS through the guarded path; per-source snapshot IDs; the
  clipped network** (2026-09-03; Planning Baseline v1.0; the first M3
  packet after the gate; no JVM):
  - **Per-source snapshot IDs** (ADR-0008, owner decision at EP-11):
    `phillysim.pipeline.SNAPSHOT_ID` becomes the mapping `SNAPSHOT_IDS`;
    the five sources acquired on 2026-09-02 keep that ID, the two routing
    sources carry `2026-09-03`; the `acquire` stage's `snapshot_id`
    parameter becomes `snapshot_ids` (the change re-ran `acquire`, which
    re-used the five verified snapshots and fetched only the new ones);
    every document that named the constant updated.
  - `phillysim.adapters.osm` (`osm_network`): Geofabrik's **dated**
    Pennsylvania extract `pennsylvania-260831.osm.pbf` (345,912,530 B; OSM
    data of 2026-08-31; never the `-latest` file) stored as delivered with
    the provider's MD5 sidecar fetched through the same path; the MD5 is
    pinned in the adapter and compared against the file and the sidecar
    before admission; the region page archived as `terms.html` and checked
    for "created by OpenStreetMap Contributors" and "License: ODbL"; a
    1 GiB file cap and no archive guard (a PBF is not a zip, and the
    download path now never opens a non-archive as one); **the first
    Bucket B manifest of the real pipeline** (ODbL, "© OpenStreetMap
    contributors"). `read` (for `validate`) opens the header only: the MD5
    checks, the generator, the replication timestamp, the sorting, and a
    bounding box that must enclose the county bounds. **The clip**
    (`osm.clip`, pyosmium): every way with a node inside the county bounds
    buffered by 5 km in the analysis CRS (ADR-0007, ADR-0008) with all of
    its nodes, the restriction relations among them, the source order, the
    box in the header; `osm.check_clip` is the clip's contract. Data card
    `docs/data-cards/osm-network.md`; DATA-LICENSES record.
  - `phillysim.adapters.septa_gtfs` (`gtfs`): SEPTA's GTFS release
    **`v202609060`** (`gtfs_public.zip`, 21,555,258 B, SHA-256 pinned as
    GitHub records it; `google_bus.zip` and `google_rail.zip` inside)
    stored as delivered; the developer license agreement archived as
    `terms.html` and checked for its two "SEPTA reserves the right …"
    sentences; allowlist `github.com`, the release-asset hosts
    (`objects.githubusercontent.com` as the packet recorded it and
    `release-assets.githubusercontent.com` as observed), and
    `www3.septa.org`; caps 128 MiB / 1 GiB / ratio 50 / 50 members on the
    outer zip at acquisition and on each inner zip in place (a new nested
    guard, `guards.inspect_nested_zip`) and again as a file; Bucket A with
    a `license_note` stating SEPTA's terms and the facts-not-contents
    position. `read` returns one row per feed (required files and columns,
    `feed_info.txt` dates covering the pinned Wednesday 2026-09-23 and
    Saturday 2026-09-26, services on both, the time zone, stops and stops
    outside the routing box as information, routes, trips); `unwrap`
    copies the two feed zips out as files, never expanded. Data card
    `docs/data-cards/septa-gtfs.md`; DATA-LICENSES record (the
    click-through agreement text as archived, accepted).
  - **The download path** (`phillysim.download`): `Fetch` gains `digest`
    (a pinned `sha256:` or `md5:` value) and `md5_of` (a provider sidecar);
    a mismatch quarantines with the new kind **`digest`**; the terms check
    reads the page's visible text (tags removed, entities decoded), so a
    phrase spanning an inline element matches; `Acquisition` records the
    digests checked. `contracts.ColumnSpec` gains `maximum`.
    `preflight` lists `osmium` among the locked packages.
  - **The `network` stage** (`phillysim.network`, between `basemap` and
    `metrics`; parameters `buffer_m` 5000, `crs`, `node_band`, `way_band`):
    writes `intermediate/network/` (the clip
    `pennsylvania-260831-philadelphia-5km.osm.pbf` and the two feed zips)
    and `intermediate/network.json` (the box, the counts, the bucket **B**
    by derivation, the two source snapshots). Measured on the pinned
    extract: 5,803,119 nodes, 921,869 ways (224,252 highways), 3,693
    relations, 49,968,756 B, about three minutes; 14,054 bus/Metro stops
    (2,800 outside the box) and 156 rail stops (39 outside). Nothing
    downstream of it reaches `publish`: the public zone is unchanged and
    still Bucket A (`PUBLISH_SOURCES` unchanged).
  - **Dependency:** `osmium` (pyosmium 4.3.1; wheels on Windows and Linux
    for Python 3.13) joins the core dependencies and the lock; the
    dependency policy test stays green.
  - **CI samples:** `raw/osm_network/2026-09-03/`, the real extract clipped
    to the six sample tracts' bounds with the same clip (49,473 nodes,
    11,532 ways, 749 KB; ODbL, © OpenStreetMap contributors, notice in the
    samples README and its Bucket B manifest, `synthetic: false`, the
    provider's header carried over, the MD5 sidecar regenerated);
    `raw/gtfs/2026-09-03/`, a **synthetic** feed in SEPTA's layout
    (`synthetic: true`; no SEPTA feed contents committed). The five other
    samples rebuilt byte-identical. Contract tests
    `tests/contracts/test_osm_network.py` and `test_septa_gtfs.py`;
    `tests/test_network.py` (the routing box, the clip on a hand-built
    extract, its determinism, every `check_clip` violation, the nested
    guards); the download-path branches on crafted bytes (a PBF never
    zip-inspected, an MD5 sidecar mismatch, a pinned SHA-256 mismatch, the
    visible-text terms check); the integration test runs the nine stages
    on the samples with the samples' digests pinned in place of the
    providers' (`conftest.sample_pins`) and asserts the Bucket B derivation
    and the unchanged Bucket A zone; `verify` 7 of 7 snapshots, 9 of 9
    stages.
  - Docs: `docs/data-dictionary.md` (the two raw-source sections, the
    `intermediate/network/` and `network.json` entries, the `digest`
    quarantine kind, the acquisition report's `snapshot_ids` and
    `digests_checked`), `docs/DATA-LICENSES.md` (status, table, the two
    dated records, the routing-buckets paragraph, the samples paragraph),
    `docs/data-cards/README.md`, the five earlier cards (per-source IDs),
    `phillysim/README.md` (nine stages, the `network` bullet, the 490 MB
    acquisition, the EP-12 resource paragraph), the samples README,
    `roadmap/architecture.md` (stage rows 1 and 8), `roadmap/sources.md`
    (SEPTA and OSM rows acquired), `roadmap/quality.md` (seven sources
    under contract, nine stages in the integration row).
- **EP-11 — M3 refinement gate executed** (2026-09-03, documentation
  only, interactively with the owner; work commit `c6b5372`, CI run
  33799859669 green on both platforms; every recommended option accepted
  at the owner review). The carry-in check: none names M3.
  The routing spike decomposed into four S packets, one session each,
  from `_TEMPLATE.md`: `roadmap/EP-12-routing-sources.md` (the OSM
  extract via Geofabrik, the first Bucket B source of the real pipeline,
  and SEPTA GTFS pinned to a release tag, never republished; per-source
  snapshot IDs; the clipped network), `EP-13-routing-toolchain-harness.md`
  (Temurin JDK 21.0.12.1+1 and the r5py R5 7.6 jar by checksum,
  project-local; r5py 1.1.7 in an optional `routing` group, never
  imported in CI; the process-tree RSS sampler with the 22 GB kill; run
  records; the smoke route; the CI performance-smoke test),
  `EP-14-routing-run-matrix.md` (the plan file, the `route matrix`
  driver, the rehearsal, the first unattended night), and
  `EP-15-routing-verdict.md` (every criterion against the records, the
  determinism band, the forty-check hand check, the walk concordance
  against the OSMnx + scipy fallback engine, go / KILLED-BY-EVIDENCE /
  TIMEBOX-EXHAUSTED, M3 closes). New `roadmap/adr/0008-routing-toolchain-pins.md`
  records the pins, extents, dates, and decision numbers the owner
  fixed at the gate (JDK and jar checksums, the dated Pennsylvania
  extract clipped to the county plus 5 km, SEPTA release `v202609060`
  with both feeds, the pinned Wednesday 2026-09-23 and Saturday
  2026-09-26, per-source snapshot IDs, the wall criterion on the two
  core runs, the determinism band, the hand-check tolerance, no
  publication in the spike, the time box). `roadmap/README.md` "M3 —
  Routing spike" table filled; `milestones.md` M3 row, "Spikes & gates",
  the EP-11 packet count, and a new M5 carry-in; `open-questions.md`
  OQ-C points at EP-15 with the measurement fixed.
- **Roadmap: EP-11 authored by EP-10** (2026-09-03): the M3 refinement
  gate, `roadmap/EP-11-m3-refinement-gate.md`, a documentation-only S
  packet that applies the M3 carry-ins (none as of that date), fixes the
  spike's inputs, sources (OSM via Geofabrik as the first Bucket B real
  source; SEPTA GTFS never republished), pins, criteria, and outcome codes,
  answers eight recorded questions with the owner, and authors the M3
  packets from EP-12 onward as S packets. `roadmap/README.md` opens the
  "M3 — Routing spike" heading with EP-11 as its first row; `milestones.md`
  M3 row names it; the third checkpoint's due point recorded.
- **Roadmap: EP-10 authored** (2026-09-03, interactively with the owner):
  the second checkpoint packet, `roadmap/EP-10-checkpoint-2.md`, due with
  M2 done. Scope decided with the owner: a fresh-clone re-run that includes
  a full real acquisition (the refresh-drift check), docs sync over the
  real pipeline's files, a license-label sweep on the real published
  output, budgets with peak RSS still deferred to M3, a dependency-triage
  checklist, the estimate-accuracy rows for EP-5a through EP-9, and a
  pre-read of the M3 refinement gate, which EP-10 authors as its own
  documentation-only packet, EP-11. README "Checkpoints" table and
  milestones.md "Spikes & gates" updated.
- **EP-8b — basemap roads: TIGER major-roads source, roads layer, contrast
  check; M2 closes** (Planning Baseline v1.0; the second half of EP-8):
  - `phillysim.adapters.tiger_roads`: the fifth real source, the TIGER/Line
    2025 county roads file (`tl_2025_42101_roads.zip`, 1.35 MB, US public
    domain, the same Census terms page archived and checked), stored as
    delivered and filtered at first read to the primary and secondary
    feature classes (MTFCC S1100 / S1200); contract, allowlist, guard
    limits, and citation like the other Census adapters. Registered with
    `acquire` / `validate` (the `sources` parameter bump re-runs `acquire`,
    which re-uses the four existing snapshots). Data card
    `docs/data-cards/tiger-roads.md`; DATA-LICENSES record; CI sample (48
    major roads crossing the six sample tracts plus 4 local-road controls)
    cut by `build_samples.py`.
  - `phillysim.basemap`: the real pipeline's `basemap` stage between
    `snap_retailers` and `metrics`: the curated roads layer
    `curated/basemap_roads.parquet` (`linearid`, `name`, `mtfcc`,
    `route_type`, geometry in EPSG:26918; 426 roads, 1,044 km for the pinned
    snapshot) with invariants enforced in-stage (CRS, unique identifiers,
    vocabularies, valid lines inside the county bounds, every road touching
    the spine) and a report `intermediate/basemap.json` (0.0 m outside the
    tracts).
  - **Public schema version 2:** `publish` writes `basemap.geojson`, one
    file with a `layer` property per feature (the `county_boundary`
    dissolved from the spine, the `roads` from the curated layer, keyed by
    `feature_id`), the manifest gains `basemap` (file and per-layer counts)
    and a `basemap` column list; the label is derived from the zone's
    sources as for every other file (Bucket A on the real pipeline). The
    gate now declares the version it checks (a version 1 zone is refused,
    not read) and checks the basemap's layers, counts, shapes, and
    columns; one negative test per new rule. The fixture publishes a
    boundary-only basemap (no synthetic roads source; the page handles
    both shapes). Data dictionary updated (version history, basemap file
    and columns, curated roads layer, raw source section).
  - `site build` copies the basemap verbatim like every other public file
    (nothing is derived at build time any more; site schema version 2
    records the layer counts). The page draws the roads as a filtered line
    layer from the same GeoJSON source, gray `#767676`, 1.6 px for primary
    and 1.0 px for secondary roads, **above the tract fills and beneath the
    tract outlines, the county boundary, and the sites** (beneath 80 %-opaque
    fills a road shows through at 1.25:1, so the brief's "under the fills"
    wording could not meet the contrast spec); a basemap note under the
    legend names the layers and counts; `data-basemap-layers` on the root
    element reports what was drawn. The contrast table in `site/README.md`
    is measured from the page's constants by a test: 3.60:1 against the
    lightest class, 4.17:1 against the map ground, 3.22:1 against the
    no-value gray, 3.79:1 against the county boundary (all required at 3:1);
    the ratios against the mid classes and the tract outline are recorded
    as the limit of a single gray on a full-range palette.
  - Tests: `tests/contracts/test_tiger_roads.py`, `tests/test_basemap.py`
    (invariants, one negative each, the stage body, the real layer with
    `--real-data-root`), the publish, site-build, browser, and real-pipeline
    suites extended (the real pipeline on the samples now runs eight stages
    and its zone is built into a site and driven in the browser: both
    basemap layers present, no error, nothing off-origin, axe clean);
    `conftest.py` owns the sample transport and the sample-built zone and
    site fixtures.
  - **M2 closes** with this packet (roadmap/README.md): the slice is
    reproducible from a fresh clone, the license buckets are applied and
    gated, and the minimal page renders the zone over the ADR-0005 basemap.
- **EP-8a — minimal slice page** (Planning Baseline v1.0; M2; EP-8 was
  split at pickup into EP-8a / EP-8b, the roads layer of the basemap being
  the other half):
  - `site/`: a static page (vanilla ES module, MapLibre GL JS 6.7.0 vendored
    under `site/vendor/` with recorded digests, BSD-3-Clause) that renders a
    public zone and nothing else: the tracts colored by the selected
    column's build-time class over the county boundary, the facility
    points, a legend from the manifest's bin edges, an HTML table of every
    published column (and one of the sites), the data-vintage line from the
    sources' snapshot IDs and citations, and the attribution and license
    block. Labeled work in progress; QA-only columns render under the
    manifest's QA note; no request leaves the page's origin. Not deployed
    (OQ-H).
  - `phillysim.publish.sitebuild` and the CLI group `phillysim site build
    [--fixture | --data-root DIR | --public DIR] [--out DIR]` / `site serve
    [--out DIR] [--port N] [--host H]`: the site is built only from a zone
    that passes the publish gate (re-run at build time), the public files
    are copied byte for byte (digests re-checked), the county boundary is
    derived from the published tract polygons as `data/basemap.geojson`
    (labeled with the tract file's license), `site.json` records every
    digest, and the build is deterministic; the dev server is the standard
    library's, bound to loopback, with the MIME types module scripts and
    GeoJSON need.
  - Tests: `tests/test_sitebuild.py` (layout, verbatim copies, boundary
    geometry, vendored digests against `VENDOR.md`, no off-origin loads,
    determinism, refusal of a failing zone, CLI, MIME types) and
    `tests/test_site_browser.py` (Playwright + axe on the fixture-built
    page in the machine's own Chrome or Edge: map + tables rendered
    offline, vintage and attribution from the manifest, column switching,
    zero axe violations, keyboard order and 24 px targets, 320 px reflow,
    reduced motion, no-WebGL fallback; fails rather than skips in CI). CI
    adds `phillysim site build --fixture`. The suite's no-network guard now
    allows loopback only. Dev dependencies `playwright` and
    `axe-playwright-python`; `.gitattributes` keeps the vendored bytes
    exact; screenshot `docs/images/slice-page-fixture.png`.
- **EP-7 — thin-slice metric + public zone + license bucketing** (Planning
  Baseline v1.0; M2):
  - `phillysim.metrics.slice`: the real pipeline's `metrics` stage
    (`curated/tract_metrics.parquet`, the analytic table's first real
    instance, methods version `slice-qa-1`): the **QA-only** straight-line
    distance in metres from each tract's population-weighted center to the
    nearest supermarket-format SNAP retailer, metric ID `qa_straight_line_m`;
    never an access measure (methodology.md), which the ID prefix, the
    manifest flag, the gate, and the method card
    `docs/method-cards/qa-straight-line.md` all say.
  - `phillysim.publish`: the publication boundary. `bucket` (ADR-0003: a
    file's bucket is derived from its sources' manifests, Bucket B
    contagious, labels with SPDX IDs and the ODbL / OpenStreetMap notices);
    `bins` (build-time quintile classes with edges recorded in the manifest,
    ties collapsing, nulls kept); `export` (the public zone, public schema
    version 1: `manifest.json`, `tracts.geojson` / `tracts.csv` with the
    analytic table widened into `<metric>[__<category>][__<mode>]` + `_moe`
    / `_cv_tier` / `_reliability_action` / `_bin` columns, `sites.geojson` /
    `sites.csv`; WGS 84, RFC 7946 rings, six-decimal coordinates, in-file
    license labels, CSV formula-injection escaping, byte-deterministic);
    `gate` (registry and digests, derived-bucket labels, in-file labels and
    notices, bounds, escaped cells, no zone or absolute path leakage,
    prohibited vocabulary and `qa_` flags per docs/CLAIMS.md, format
    parity).
  - The `publish` stage of both pipelines declares the whole `public/`
    directory as its one output, runs the gate on the staged zone, and lets
    nothing leave the curated zone if it fails; the runner installs the
    zone atomically. The fixture's zone is Bucket B (its `osm_network`
    source is), the real slice's is Bucket A (CC BY 4.0). Adapters gain a
    `citation`, carried into every label's attribution.
  - CLI: `phillysim gate [--fixture] [--data-root DIR | --public DIR]`
    re-runs the gate on an installed zone; CI runs `gate --fixture`.
    `Pipeline.upstream_raw` names a path's raw provenance so a test holds
    the publish stage's declared sources to the DAG.
  - Tests: golden distances by hand and a brute-force check on the samples;
    bin edges by hand; escaping cases; the gate green on the fixture's zone
    and one negative per check, an intentionally mislabeled file first; the
    stage-level refusal; byte determinism; the real-pipeline integration
    test through seven stages ending in a gated Bucket A zone. Data
    dictionary: "Public zone" section (public schema v1) replaces the
    placeholder export; DATA-LICENSES "How labels are applied".
- **EP-6 — SNAP retailer adapter + supermarket-format classification**
  (Planning Baseline v1.0; M2):
  - `phillysim.adapters.snap` (`snap_retailers`): the USDA SNAP Retailer
    Locator historical file (2005–2025, as of 2025-12-31) acquired through
    the guarded path with dual URLs for the FNS→FNA rename (the pre-rename
    host redirects; the FNA download redirects to a content-delivery host,
    allowlisted), stored as delivered (24 MB zip, read in place), Bucket A;
    at first read: Philadelphia County and open authorization spells only
    (1,609 retailers). No USDA terms page is reachable by the guarded path,
    so the archived page is the provider's data page in force, checked for
    its official-site banner and its as-of sentence (a vintage change stops
    acquisition). Contract: store types within the mapped vocabulary (a new
    label is the stop condition), county / state fixed, WGS 84 points inside
    the county bounds, unique record ID.
  - `phillysim.classify.store_format`: the published, versioned store-type →
    format-class mapping (`store-formats-1`; 17 USDA labels → `supermarket`,
    `grocery`, `combination`, `convenience`, `specialty`, `farmers_market`,
    `other`; `supermarket` = USDA `Supermarket` + `Super Store`, AM-4),
    packaged as `store_formats.csv`, strict on unknown labels, rendered into
    the first method card `docs/method-cards/store-formats.md` (a test keeps
    the two in sync; `python -m phillysim.classify.store_format` re-renders).
  - `phillysim.destinations`: the real pipeline's `snap_retailers` stage →
    `curated/snap_retailers.parquet` (GeoParquet in EPSG:26918, keyed by
    `snap_retailers:<record id>`, store type, format class,
    `supermarket_format`, containing tract, coordinates as delivered,
    authorization date) with its invariants enforced in-stage, plus the
    count report `intermediate/snap_retailers.json`. One layer serves both
    the supermarket-format destinations and the all-SNAP-retailer variant
    kept for M5's SRAM comparison.
  - Tests: golden mapping test, SNAP source contract on a committed sample
    (26 retailers inside the six sample tracts + 5 control rows), layer
    invariants (one negative per check), the real-pipeline integration test
    through five stages; data card `docs/data-cards/snap-retailers.md` with
    the sanity check against USDA's year-end totals.
  - Runner: a stage that now declares an output it never produced is stale
    (`changed: declared outputs`); `acquire` takes the source list and
    snapshot ID as parameters, so registering a source re-runs it for the
    new source only; the Windows install retry now waits up to about 14 s.
    `build_samples.py` pins the dBASE header date so the TIGER sample is
    byte-identical on any day.
- **EP-5b — curated tract spine + geospatial invariants + analysis-CRS ADR**
  (Planning Baseline v1.0; second half of the EP-5 set, which is now
  complete):
  - **ADR-0007**: the analysis CRS is EPSG:26918 (NAD 83 / UTM zone 18N,
    metres), with the alternatives (State Plane feet and metres, NAD83(2011),
    Web Mercator, geographic) and the publication-boundary datum note
    recorded; pinned in `phillysim.spine.ANALYSIS_CRS` and the `spine`
    stage's `crs` parameter; methodology.md and the data dictionary point at
    it, and the dictionary now says which tables carry which CRS.
  - `phillysim.spine`: the real `spine` stage (`curated/tracts_spine.parquet`:
    TIGER geometry reprojected into the analysis CRS, CenPop 2020 population
    and population-weighted centers joined one-to-one, keyed by GEOID, 408
    rows) and `demographics` stage (`intermediate/acs_tracts.parquet`: the
    pinned ACS estimates and MOEs joined one-to-one to the spine, nulls
    kept), both registered in the real pipeline after `validate`, plus the
    geospatial invariant module `check_spine` (CRS as declared, geometry
    valid and inside the county bounds, GEOID pattern / uniqueness / count,
    one center and one ACS row per tract) that both stages enforce on their
    own output.
  - `tests/test_spine_invariants.py`: the invariants on the committed samples
    (positive, and one negative per check) in CI, and on the real spine with
    the new `pytest --real-data-root DIR` option (skipped otherwise; the
    real-run result is in the EP-5b handoff). The real-pipeline integration
    test now covers all four stages.
  - Data cards for the three spine sources under `docs/data-cards/` (what
    each contributes, vintage, terms, CRS, known limits, claims-matrix
    notes).
- **EP-5a — spine source adapters: acquisition path + TIGER/CenPop/ACS
  snapshots** (Planning Baseline v1.0; first half of the EP-5 set):
  - `phillysim.download`: the guarded outbound acquisition path, in a fixed
    order: allowlist before any connection (https only, redirect targets
    checked, no plain-http handler), timeout and bounded backoff (three
    attempts per URL, 1 s / 2 s / 4 s, definitive failures fall through to
    the alternate URL), capped streaming through `copy_capped` under
    per-source `Limits`, zip guards before anything could be extracted, the
    terms page in force archived beside the data and checked for expected
    wording (drift quarantines the snapshot with the new reason kind
    `terms`), manifest via the manifest engine, admission only through
    `quarantine.admit`. Injectable transport; an optional query secret is
    never recorded.
  - `phillysim.adapters`: `tiger_tracts` (TIGER/Line 2025 Pennsylvania
    tract zip, read from the zip in place), `cenpop` (CenPop2020 tract
    centers), and `acs` (ACS 5-year 2020–2024 tables B01003 and B08201
    from the key-free table-based summary file, annotation values nulled),
    each with its own allowlist, limits, terms phrase, Bucket A license
    note, `SourceContract`, and a county filter applied at first read
    (every file is stored as delivered so it stays verifiable against the
    provider).
  - `phillysim.pipeline`: the real pipeline (`real`) registered behind
    `phillysim run / status / verify` without `--fixture`, with `acquire`
    (pinned `SNAPSHOT_ID = 2026-09-02`; existing verified snapshots re-used,
    never re-downloaded or replaced; `intermediate/acquisition.json`
    report) and `validate` (`intermediate/validation.json` with rows, nulls,
    violations). Same stage names, zones, and paths as the fixture
    pipeline; separate root and pipeline name.
  - First real snapshots acquired on 2026-09-02 (408 Philadelphia County
    tracts in each source, no contract violations); dated records in
    `docs/DATA-LICENSES.md`; raw-source sections in `docs/data-dictionary.md`.
  - `tests/fixtures/spine-samples/`: real-shaped, US-public-domain subsets
    of the three snapshots (six tracts plus control rows) with a README and
    the deterministic script that cuts them; contract tests and real
    pipeline integration tests run on them offline.
  - Tests: 61 new (301 total). `tests/conftest.py` now disables sockets for
    the whole suite, so no test can reach the network.

### Changed

- Stage runner (EP-5a fixes): the atomic install of a stage output retries
  a transient `PermissionError` a bounded number of times (a Windows virus
  scanner held the freshly downloaded 13 MB TIGER zip during the first real
  run), and the state-file scrub also replaces the repr-escaped (doubled
  backslash) form of the data root that Windows `OSError` messages carry.
- **EP-9 — checkpoint 1** (after M1, before M2; 2026-09-02). Fresh clone of
  `main` at `a72d318` re-run green: `uv sync --locked`, 240 tests,
  `phillysim run --fixture` (11 ran, then 0 ran / 11 skipped), `status`
  (11 fresh), `verify` (8 of 8 snapshots, 11 of 11 stages). Documentation
  synced to the code: `roadmap/architecture.md` names the eleven stages
  under "Data flow"; `docs/data-dictionary.md` lists the five intermediate
  files as undocumented by policy and describes the placeholder public
  export; `docs/DATA-LICENSES.md` names the manifest fields the engine owns
  and flags the placeholder `publish` output as unlabeled until EP-7;
  `roadmap/quality.md`'s test matrix says which rows exist today; the root
  README's status paragraph ("no pipeline logic exists yet") and the
  fixture README's description of `verify --fixture` were corrected.
  License-label sweep clean (no tracked file under any `public/` zone;
  fixture buckets agree with their contracts). Resource baselines recorded
  in `phillysim/README.md`. `roadmap/milestones.md` gains an "Estimate
  accuracy" table (EP-1–EP-4b, all one session) and the re-plan trigger
  evaluation (none fired). One setup finding: a Windows fresh clone in a
  deep directory fails with "Filename too long" on two vendored
  `source material/` file names; both READMEs now say to clone with
  `core.longpaths=true`. EP-5 pre-read: does not fit one session; split
  into `EP-5a-spine-acquisition.md` (download path, TIGER / CenPop / ACS
  adapters, contracts, samples, real pipeline registration) and
  `EP-5b-spine-curated.md` (curated spine, invariant tests, ADR-0007
  analysis CRS, data cards); the bare EP-5 file now describes the set; M2
  table rows updated.
- Roadmap: first checkpoint packet authored as
  `roadmap/EP-9-checkpoint-1.md` (owner decisions, 2026-09-02): the five
  milestones.md checkpoint items plus the EP-5 pre-read and split decision;
  a "Checkpoints" table in `roadmap/README.md` between M1 and M2, EP-5 now
  depends on EP-9; the estimate-accuracy record will live in a new
  milestones.md table; the CI performance-smoke test is deferred to the M3
  spike, baselines only for now.
- tinycity: tract polygon corners are rounded to six decimals like every
  other fixture coordinate, so the spine stage's output read back from the
  GeoJSON snapshot equals the golden geometry exactly. Only
  `expected/tracts_spine.parquet` (content) and its `CHECKSUMS.txt` line
  changed; the raw snapshots are byte-identical (EP-4b).
- Delisting window in `docs/policies.md` is now two-tier: 7 days for standard
  requests, 72 hours for safety-motivated requests (owner decision,
  2026-09-02; resolves the EP-1 carry-over).
- OQ-A (City license confirmation) **closed**: the address used on
  2026-08-23 did not exist and the message bounced; the request was re-sent
  on 2026-09-02 to the contact the City's Open Data Program page lists, and
  CityGeo (Office of Innovation & Technology) replied the same day that no
  terms exist beyond the published open-data terms page and the data is
  shared for any use that benefits the community. `docs/DATA-LICENSES.md`
  and `roadmap/sources.md` now record the confirmed position; the caveat
  wording is retired, takedown readiness stays standing policy.
- Dependabot no longer opens PRs against the vendored `source material/`
  JKAN tree: `bundler` and `npm` entries with `open-pull-requests-limit: 0`
  added to `.github/dependabot.yml`; PRs #1–#4 closed and the seven open
  alerts for that path dismissed as "not used" (owner decision, 2026-09-02).
  The tree is reference material that is never built, executed, or
  modified, so the alerts describe no exposure.
- Roadmap status surface: `roadmap/README.md` now carries per-milestone
  work-packet tables (packet, size, depends-on, status) as the place packet
  and milestone status is tracked, mirroring the sibling repositories'
  owner-facing roadmaps while keeping this repo's `[ ]` / `[~]` /
  `[x] <commit>` convention and unpadded `EP-N` numbering. M0 is recorded
  done at `9bcb7b2` (both packets done; go/no-go met). `milestones.md`
  gains a Packets column and points to the tables.
- Packet sizing: one packet is one session from 2026-09-02 on. The only L
  packet, EP-4, is split at its engine/runner boundary into
  `EP-4a-manifest-engine.md` (zones, manifests, guards, quarantine,
  snapshot-level `verify`) and `EP-4b-stage-runner.md` (stages,
  fingerprints, resume/cancel, preflight, `run/status/verify --fixture`).
  A lettered-split convention (`EP-Na`, `EP-Nb`, …, number kept) is
  documented as the pickup remedy for the remaining M packets (EP-5–EP-8);
  new packets are never authored above one session. `_TEMPLATE.md` updated;
  EP-5's prerequisite, the data dictionary, and the fixture README now cite
  EP-4a/EP-4b.
- `roadmap/milestones.md` gains a "Refinement-gate carry-ins" section, and
  the roadmap README's reading order points to it: deferred obligations from
  earlier packets are applied when a later milestone's EP files are
  authored. First entry: the M5 reliability conventions (OQ-I) with the
  locked-decision text, baseline check, apply list, and regression guard.

### Added

- **EP-4b — stage runner: fingerprints, resume/cancel, preflight,
  `phillysim run/status/verify`** (Planning Baseline v1.0; completes M1):
  - `phillysim.stages`: the stage registry. A `Stage` declares inputs and
    outputs as data-root-relative paths plus JSON parameters; a `Pipeline`
    validates the wiring as a DAG (every input external under `raw/` or
    produced by an earlier stage; every output produced once). Cooperative
    `CancelToken` with checkpoints inside stages.
  - `phillysim.runner`: fingerprint = SHA-256 of the inputs' content digests
    plus the parameters, recorded per stage in `<data root>/pipeline_state.json`
    (shape in `docs/data-dictionary.md`); a stage is skipped while its
    fingerprint is unchanged and its outputs are intact. Outputs are written
    to `cache/staging/<stage>/` and installed by atomic rename, so a failed
    or cancelled stage never leaves a partial file in a zone; it is recorded
    as incomplete and the next run resumes from it. `status` (fresh / stale /
    missing / incomplete) and `verify_state` (state file vs. zones: outputs
    present and unaltered, no incomplete stage, no leftover staging, no
    unknown record). The raw zone stays immutable under the runner.
  - `phillysim.preflight`: free disk, physical RAM, Python version, the six
    locked packages, writable root; every check reported in one pass and any
    failure refuses the run. Real-run thresholds from architecture.md
    (≥150 GB free disk, 24 GB RAM); fixture-scale thresholds for `--fixture`,
    labelled as such. No new dependency (RAM via Win32 / `/proc/meminfo` /
    `sysconf`).
  - `phillysim.fixtures.pipeline`: the eleven fixture stages (`acquire`,
    `validate`, `spine`, `demographics`, `destinations`, `conflate`, `hours`,
    `network`, `travel_times`, `metrics`, `publish`) carrying tinycity from
    generated raw snapshots (admitted through the EP-4a guards) to the
    expected tables; `hours` and `travel_times` are explicit stubs fed by the
    generator's oracle until M4 / M3; `publish` writes a plain CSV until
    EP-7 adds license bucketing. The four curated outputs equal the golden
    tables by content.
  - CLI: `phillysim run [--fixture] [--data-root DIR] [--stage NAME]
    [--param stage.key=value]`, `phillysim status [--fixture]`, and
    `phillysim verify` extended with stage-state coherence; `--fixture` now
    targets the fixture pipeline's own data root, `<data root>/fixture/`
    (gitignored, as is the state file).
  - CI runs `phillysim run --fixture`, `status --fixture`, and
    `verify --fixture` on Windows and Linux: the M1 go/no-go criterion.
  - Tests: 33 new (240 total): runner unit tests (registry rules,
    content-hash fingerprints, skip / rerun-only-dependents / resume after an
    injected failure / cancel at a checkpoint and between stages / immutable
    raw / no absolute paths in the state file), preflight negative tests with
    injected probes, and the integration suite on tinycity via the CLI.

- **EP-4a — manifest/snapshot engine, zones, download guards, quarantine**
  (Planning Baseline v1.0):
  - `phillysim.zones`: source-name and snapshot-ID rules (`YYYY-MM-DD`,
    `-N` same-day sequence), snapshot listing, stray-entry detection, and
    the one function that creates the zone layout (resolution still never
    does).
  - `phillysim.manifest`: the snapshot manifest as an owned model with every
    field rule enforced (UTC timestamp, http(s) URL without credentials,
    license bucket A/B, integer schema version, bare file names, 64-hex
    digests, terms archive listed), a canonical reader/writer that
    round-trips byte-for-byte, and `verify_snapshot` / `verify_raw_zone`
    naming every missing, altered, unlisted, or relocated file.
  - `phillysim.guards`: domain allowlist (https only, subdomain match, no
    IP literals or credentials), size cap before and during streaming,
    zip-slip path normalization (absolute paths, drive letters, `..`,
    symlink members), decompression-bomb ceilings (declared size, ratio,
    member count, actual bytes), plus guarded zip / gzip extraction. No
    adapter knowledge; allowlist and limits are always passed in.
  - `phillysim.quarantine`: default-deny `admit` (manifest → guards →
    checksums); any failure moves the whole snapshot to
    `data/quarantine/<source>/` and writes a reason file beside it.
  - `phillysim verify [--fixture | --raw DIR]`: snapshot-level verification
    with a per-snapshot report and non-zero exit on any failure.
  - Tests: 131 new (207 total) including one crafted negative input per
    guard, each shown to be refused *and* quarantined; a tampered byte in a
    fixture file fails `verify` naming the file; every manifest field shown
    required and every malformed form rejected.
  - The tinycity generator now builds its manifests through the engine; the
    committed fixture was regenerated for both variants and did not change
    by a byte (the "proposed" shape is now the owned shape, schema version
    still 1). Data dictionary manifest section promoted to owned and a
    quarantine reason-file section added.
- **EP-3 — tinycity synthetic fixture + source-contract harness** (Planning
  Baseline v1.0):
  - `phillysim gen-tinycity`: deterministic generator for a wholly synthetic
    mini-geography (six fake tracts in the open Atlantic, thirteen destination
    points across all three v1 categories, fake ACS with margins of error
    covering all three CV tiers, tiny GTFS and street-network stubs, a
    precomputed travel-time matrix standing in for routing until M3, and
    golden expected tables). Committed under
    `phillysim/tests/fixtures/tinycity/` with `CHECKSUMS.txt`; an
    `--variant invalid` copy with eight injected faults under
    `tinycity-invalid/`.
  - Hours edge cases from methodology.md Tier 2 (weekend-only, seasonal,
    missing, malformed) with hand-derived open/closed answers for the pinned
    analysis weeks.
  - `phillysim.contracts`: adapter-agnostic source-contract harness (schema,
    key, row-count, license bucket + schema version, geometry type / CRS /
    validity / bounds) and the locked analytic-table contract
    `{estimate, moe, cv_tier, reliability_action}`.
  - Tests: two-run byte determinism, committed-fixture currency, harness
    negative tests for every check kind, every injected fault caught.
  - `docs/data-dictionary.md` seeded at schema version 1.
- **EP-2 — Python scaffold + offline CI skeleton** (Planning Baseline v1.0):
  - `phillysim/` uv project: `pyproject.toml` declaring the locked stack
    (typer, geopandas, pyogrio, shapely, pyproj, duckdb, pyarrow), committed
    `uv.lock`, CPython pinned to 3.13 (`>=3.12` declared). Every dependency
    installs from wheels on Windows.
  - Typer CLI entry point: `phillysim --help`, `version`, `paths`.
  - Config module resolving the app-owned `data/` root (env override, then
    repo root, then working directory); no absolute paths anywhere.
  - Tests: smoke, config, and dependency policy (GDAL/fiona ban, ADR-0001,
    with built-in negative checks so the guard is proven on every run).
  - `.pre-commit-config.yaml` (ruff via uv; pre-commit-hooks v6.0.0).
  - `.github/workflows/ci.yml` (SHA-pinned actions, read-only token,
    Windows + Linux matrix, fixtures only) and `.github/dependabot.yml`
    (uv + GitHub Actions ecosystems, monthly).
  - Package README with setup commands; setup sections in the root README
    and CONTRIBUTING.
- **EP-1 — repository governance bootstrap** (Planning Baseline v1.0):
  - README rewritten to the charter framing: measuring access, not modeling
    outcomes; the "sim" name explained; AI disclosure; non-endorsement.
  - `.gitignore` covering data zones, secrets, caches, logs, notebook
    checkpoints, and local databases.
  - `docs/CLAIMS.md` — claims matrix instantiated verbatim from charter.md.
  - `docs/DATA-LICENSES.md` — pre-acquisition stub: City-license caveat,
    ODbL/CC BY output buckets (ADR-0003), source terms summary.
  - `docs/policies.md` — correction channel and delisting/takedown policy.
  - `CONTRIBUTING.md` and `SECURITY.md`.
  - This changelog.

### Earlier

- Planning Baseline v1.0 accepted; roadmap package added (`roadmap/`:
  charter, scope, sources, methodology, architecture, governance, quality,
  milestones, packets EP-1..EP-8, ADRs 0001–0006).
- MIT license added; OpenDataPhilly JKAN tree vendored under
  `source material/` for reference, provenance documented.
