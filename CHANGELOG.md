# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
the axes in [roadmap/quality.md](roadmap/quality.md) (ADR-0006) — code is
SemVer 0.x pre-v1, and data snapshots, schema, and method versions are
recorded separately in manifests once the pipeline exists.

## [Unreleased]

### Added

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
