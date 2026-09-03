# EP-8b — Basemap roads: TIGER major-roads source, roads layer, contrast check; M2 closes

**Status:** [x] 5cb5092 (done 2026-09-03) · **Milestone:** M2 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-8 (2026-09-02, pickup pre-read; EP-8a is the other half)

## Outcome & value
The minimal public-domain basemap ADR-0005 describes, complete for v1:
county boundary (EP-8a) **plus major roads** from TIGER/Line, grayscale,
meeting the UI contrast spec so the thematic layer stays legible over it.
The roads arrive the way every other source does: a guarded acquisition
with a terms archive, a manifest, a contract, CI samples, and a data card;
they leave through the publish gate as a labeled public-zone file, so the
site keeps reading the public zone and nothing else. With this the EP-8
set's outcome is met and **M2 closes** (this packet carries the
milestone-level evidence: the slice reproducible from a fresh clone, license
buckets applied, minimal page rendering).

## Scope
- in: `tiger_roads` adapter (TIGER/Line 2025 primary + secondary roads for
  Pennsylvania, or the Philadelphia County roads file filtered to MTFCC
  S1100 / S1200; decide on size and clip to the county at first read as the
  other TIGER adapters do); registration in the real pipeline's `acquire` /
  `validate` (`sources` parameter bump re-runs `acquire`); a curated roads
  layer in the analysis CRS; a public-zone `basemap` layer (roads +
  boundary) with the label derived from its sources (Bucket A), which means
  a **public schema version bump to 2** (new file, new manifest member) and
  the gate extended for it; `sitebuild` takes the basemap from the zone
  instead of deriving it; the page draws roads under the tract fills at a
  muted gray whose contrast against the fills and the boundary meets the
  spec (3:1 for meaningful boundaries; text 4.5:1); CI samples cut for the
  six sample tracts; data card `docs/data-cards/tiger-roads.md`; the
  fixture pipeline gains a synthetic roads source or the fixture's basemap
  stays boundary-only (decide; the page must handle both).
- out (explicit non-scope): road labels, PMTiles (OQ-F), water and parks,
  anything M6.

## Prerequisites & locked decisions
- prerequisites: EP-8a.
- locked decisions honored: ADR-0005; ADR-0007 (analysis CRS; WGS 84 only
  in `public/`); ADR-0003 (derived buckets); the download-path order and
  the terms-archive stop condition (EP-5a); the contrast spec.
- dependencies: TIGER/Line 2025 roads on `www2.census.gov` (public domain;
  the Census open-data terms page already archived for the spine sources).

## Safety preconditions
Standing policy. Packet-specific: the roads file is stored as delivered and
clipped at first read; the public roads file passes the gate (bounds,
label, no leakage); the schema bump is recorded in the data dictionary; the
page's contrast numbers are measured and written down, not asserted.

## Likely components & contracts (proposed)
`adapters/tiger_roads.py`; `pipeline.py` (`PUBLISH_SOURCES` +
`tiger_roads`, a `basemap` stage or an extension of `publish`);
`publish/export.py` (`basemap.geojson`, `PUBLIC_SCHEMA_VERSION = 2`),
`publish/gate.py`; `publish/sitebuild.py`; `site/main.js` (roads layer);
`tests/fixtures/spine-samples/raw/tiger_roads/`; `build_samples.py`;
`docs/data-cards/tiger-roads.md`; `docs/data-dictionary.md`.

## Implementation notes
Read EP-5a's handoff for the acquisition pattern and EP-7's for the
public-zone shape. A code-only change to `publish` needs the schema bump to
re-run (fingerprints never include code). Keep the site's basemap contract
one file (`basemap.geojson` with a `layer` property per feature) so the page
written in EP-8a needs only a second line layer. Measure contrast with the
palette's lightest class over the road gray and record the ratios in the
site README.

## Acceptance criteria & evidence
- [x] Roads acquired, validated, curated, published, gated, and drawn;
  fresh-clone run reproduces the zone byte for byte (digests recorded).
- [x] Contrast ratios recorded and within spec; axe and the browser tests
  stay green.
- [x] M2 go/no-go recorded: slice reproducible from a fresh clone, license
  buckets applied, page renders; README milestone heading closed.
- Evidence: CI green; handoff digests; screenshot updated.

## Tests / validation
Contract tests on the samples; gate negatives for the new file; browser
tests; `pytest --real-data-root ../data` for the real layer's invariants;
fresh-clone rehearsal.

## Resource budget
Network: the roads file (tens of MB for the state file; a few MB for the
county file). Otherwise trivial.

## Risks, rollback, stop condition
The state-wide primary/secondary file may be large for a 408-tract clip:
prefer the county roads file filtered by MTFCC if so. Stop and escalate if
the Census terms page changes wording (quarantine, as the download path
does).

## Documentation / ADR updates
Data card; data dictionary (public schema 2); sources.md row for the
basemap made concrete; site README (contrast table); CHANGELOG;
`roadmap/README.md` (row and the M2 heading); this file's handoff.

## Handoff payload (filled 2026-09-03)
- **Packet:** EP-8b — done at commit `5cb5092` (+ this status commit).
  Planning Baseline v1.0. The second half of the EP-8 split; it fit one
  session. CI run
  [33710988366](https://github.com/willtfarrington/phillysim/actions/runs/33710988366)
  on `5cb5092` green on `windows-latest` and `ubuntu-latest` (pytest with
  the browser modules, ruff, the four fixture-pipeline steps, `gate
  --fixture`, `site build --fixture`; no browser download, CI hosts
  unchanged).
- **Files changed:** new `phillysim/src/phillysim/adapters/tiger_roads.py`,
  `phillysim/src/phillysim/basemap.py`,
  `phillysim/tests/contracts/test_tiger_roads.py`,
  `phillysim/tests/test_basemap.py`,
  `phillysim/tests/fixtures/spine-samples/raw/tiger_roads/2026-09-02/`
  (zip, terms excerpt, manifest), `docs/data-cards/tiger-roads.md`; changed
  `adapters/{__init__,base}.py` (registry; `COUNTY_NAME`), `pipeline.py`
  (`tiger_roads` in `SOURCES` and `PUBLISH_SOURCES`, the `basemap` stage,
  `publish` inputs and body), `fixtures/pipeline.py` (boundary-only basemap,
  `FIXTURE_BOUNDARY_NAME`), `publish/export.py` (`basemap.geojson`,
  `basemap_features`, `boundary_name` / `roads` parameters),
  `publish/gate.py` (`PUBLIC_SCHEMA_VERSION = 2` now declared here, the
  `basemap` manifest member and `_check_basemap`), `publish/sitebuild.py`
  (no derivation; verbatim copy; site schema 2), `cli.py` (build summary),
  `site/{index.html,main.js,README.md}` (roads layer, basemap note,
  `data-basemap-layers`, six downloads, contrast table),
  `tests/conftest.py` (`SampleTransport` moved here; `sample_transport`,
  `sample_public_zone`, `sample_built_site` fixtures),
  `tests/{test_publish,test_sitebuild,test_site_browser}.py`,
  `tests/contracts/test_spine_sources.py`,
  `tests/integration/{test_real_pipeline,test_fixture_pipeline}.py`,
  `tests/fixtures/spine-samples/{build_samples.py,README.md}`,
  `docs/images/slice-page-fixture.png` (regenerated at 1200 × 1600 so the
  basemap note is in frame), `docs/{data-dictionary,DATA-LICENSES}.md`,
  `docs/data-cards/README.md`, `roadmap/{README,architecture,quality,
  sources}.md`, `phillysim/README.md`, `README.md`, `CHANGELOG.md`, this
  file.
- **Commands/tests run + results.** Working clone: `uv run pytest` → 461
  passed, 3 skipped (the real-data tests; 423 passed, 2 skipped before the
  packet) in 30 s; `ruff check` / `ruff format --check` clean; `pre-commit
  run --all-files` all hooks passed; diff scanned for usernames and
  absolute paths → none; `pytest tests/test_spine_invariants.py
  tests/test_basemap.py tests/test_slice_metric.py --real-data-root
  ../data` → every invariant holds on the real layers (spine digest
  unchanged; roads layer 426 rows). **Real run, working clone (`data/`):**
  `phillysim run` re-ran `acquire` (7.2 s: the roads zip 1,352,071 bytes in
  0.3 s and its terms page, one attempt each, the four other snapshots
  verified and re-used), `validate` (3.3 s, 426 roads, no violation),
  `spine` and `snap_retailers` (stale on `validation.json`; byte-identical
  outputs), `basemap` (0.3 s), `publish` (0.6 s; stale on the
  `public_schema_version` parameter), about 15 s wall; `gate` green (5
  files Bucket A / CC-BY-4.0, 4 sources); `status` 8 fresh; `verify` 5 of 5
  snapshots, 8 of 8 stages; `site build` on the real zone and headless
  Chrome: `data-map="ready"`, `data-basemap-layers="county_boundary roads"`,
  no console error, no request off the dev server's origin, six downloads.
  **Second data root** (scratch, from empty): 8 stages in 17.5 s wall
  including the 122 MB acquisition; every public and curated digest equal
  to the working clone's (below). **Fresh-clone rehearsal of `5cb5092`** (scratch directory, `git clone -c
  core.longpaths=true` from GitHub, deleted afterwards): clone 1 s; `uv
  sync --locked` 7 s; `uv run pytest` 461 passed, 3 skipped (41 s, cold
  caches); `phillysim run` acquired all five sources (7.5 s incl. 122 MB;
  the roads zip 1,352,071 bytes in 0.3 s), validate 3.1 s, spine 0.2 s,
  demographics 0.8 s, snap_retailers 2.3 s, basemap 0.3 s, metrics 0.0 s,
  publish 0.5 s (16 s wall); second `run` 0 ran / 8 skipped; `status` 8
  fresh; `verify` 8 of 8; `gate` green; `site build` reports
  `county_boundary (1), roads (426)`; `git status` clean; data root 121 MB;
  every digest below identical to the working clone's; 75 s in all.
- **Reproducibility reference (byte-identical between the working clone,
  the second root, and the fresh clone):** `public/basemap.geojson` sha256
  `04141abb6aba057f8f8bbd26e9544876541dbb9881284a125f7b209a7320eafd`
  (588,768 bytes; 140 KB gzipped), `public/manifest.json`
  `7f2a19d4160b208ff89180a6f07f9822fc86acfae1b7282c2ca6594091a7c702`,
  `public/tracts.geojson`
  `18e6f19c1eecb3d38ce7f2934a9378b116c5b4c0c9f33b35a502e1dd59336191`
  (875,603 bytes; the in-file schema version and attribution changed, the
  features did not), `public/sites.geojson`
  `65962e5371e98ac91c2dcf5505e64616a6d2cb8cb987fecde780c1f4a8aa0403`,
  `public/tracts.csv` `ce380762…d5ce5` and `public/sites.csv`
  `ea3bdea9…f1a3` unchanged from EP-7; `curated/basemap_roads.parquet`
  `70469c4e484fda28c7f249834c740e72b0cfd0de8eb6caaa8f7cf37bd47f66ee`
  (271,871 bytes); `curated/tract_metrics.parquet` `fa8b8bdd…4b9ce`,
  `curated/tracts_spine.parquet` `0c1d2349…fd3a2`, and
  `curated/snap_retailers.parquet` `a2887ec3…b63b` unchanged. Raw roads zip
  `tl_2025_42101_roads.zip` sha256 in the manifest.
- **The roads, as measured:** 426 primary and secondary roads (46 S1100,
  380 S1200; route types 9 I, 27 U, 60 S, 330 M; none unnamed), 1,044.371
  km, 0.0 m outside the spine's tract union (the county file is the county
  scope; nothing clipped). CI sample: 48 major roads crossing the six
  sample tracts (9 S1100, 39 S1200) plus 4 local-road controls.
- **The page, as measured (contrast, WCAG 2.x ratios from the constants in
  `main.js`, pinned by test):** road gray `#767676` vs lightest class
  `#fde725` 3.60:1, vs darkest class `#440154` 3.35:1, vs map ground
  `#f5f5f5` 4.17:1, vs no-value gray `#d9d9d9` 3.22:1, vs county boundary
  `#1b1b1b` 3.79:1 (all required at 3:1, all met); tract outline `#555555`
  vs lightest class 5.91:1; county boundary vs lightest class 13.64:1 and
  vs ground 15.80:1. Recorded, not required: road vs classes 2–4 2.16 /
  1.19 / 1.67:1, road vs tract outline 1.64:1 (a single gray cannot reach
  3:1 against every class of a full-range palette; the roads are a
  reference layer under the meaningful boundaries, distinguished by width
  and stacking too). Roads beneath the 80 %-opaque fills would show
  through at 1.25:1 (1.59:1 for black), which is why they are drawn above
  the fills. axe: zero violations on the fixture page and on the
  sample-built real page; keyboard order unchanged from EP-8a.
- **M2 go/no-go evidence (this packet carries the set's milestone
  evidence):** the slice is reproducible from a fresh clone (digests above,
  identical across three roots); the license buckets are applied per file,
  derived from the sources, and gated (Bucket A on the real zone, Bucket B
  on the fixture, both in CI); the minimal page renders the zone over the
  ADR-0005 basemap (county boundary plus TIGER major roads) with axe and
  the browser tests green on both platforms. `roadmap/README.md`'s M2
  heading is closed on that evidence.
- **Resource observations:** one session, at the S estimate. Network: 1.35
  MB for the roads file (the state PRISECROADS file, 15.5 MB, was rejected
  on size in favour of the county file); a fresh acquisition is now 122 MB.
  Raw zone +1.7 MB (data root 120 MB); roads layer 272 KB; the public zone
  1.5 MB (about 330 KB gzipped) with `basemap.geojson` 589 KB (140 KB
  gzipped), the built site 2.8 MB; stages under a second except `acquire`
  and `validate`. Suite 461 tests in 30 s (the sample-built real zone and
  its browser run add about 5 s). Guard `Limits` for `tiger_roads`: 16 MiB
  file / 64 MiB extracted / ratio 50 / 20 members (actual 1.35 MB, seven
  members, 3.5 MB extracted).
- **Decisions made (owner-reviewed 2026-09-03, all four recommended options
  accepted):**
  - **Commit, push, CI, fresh-clone rehearsal, handoff:** done as above.
  - **Roads z-order (deviation from the brief's wording):** the brief said
    "under the tract fills"; measured, a road beneath the 80 %-opaque fills
    shows through at 1.25:1 against the lightest class (1.59:1 even if
    black), so no gray under the fills can meet the 3:1 spec. Accepted:
    roads are drawn **above the fills and beneath the tract outlines, the
    county boundary, and the sites**, in `#767676`, with the ratios in the
    site README pinned by test.
  - **Screenshot policy kept:** the committed image stays the fixture's
    (regenerated with the basemap note in frame); the real-data screenshot
    was made for the review and not committed, as at EP-8a.
  - **M2 closed** on this packet's evidence (above).
  - Routine (agent's call, logged): the **county roads file** rather than
    the state primary/secondary file (1.35 MB against 15.5 MB; the provider's
    own county scope, so the county filter of the other TIGER adapters
    becomes a feature-class filter, MTFCC S1100 / S1200 at first read,
    recorded in the adapter's filter note; the `basemap` stage verifies the
    scope against the spine instead of cutting geometry); the fixture's
    basemap stays **boundary-only** (no synthetic roads source: the golden
    tables and the fixture generator stay untouched, the page handles both
    shapes, and the roads path is exercised in CI by the real pipeline on
    the committed samples, built into a site and driven in the browser);
    the basemap is **one public file** with a `layer` property per feature
    keyed by `feature_id` (`county_boundary`, `roads:<linearid>`), every
    feature carrying the same columns, the boundary dissolved from the
    spine in the projected CRS at publish time, so the site derives nothing
    any more; the file carries the **zone-wide label and sources** like
    every other file (EP-7's design), which makes it Bucket A on the real
    pipeline; the gate now **declares the schema version it checks** and
    refuses any other (a stale version 1 zone is rebuilt, never read),
    with `PUBLIC_SCHEMA_VERSION` moved to `gate.py` so the exporter imports
    it; the `basemap` stage sits between `snap_retailers` and `metrics`
    (parameters `crs` and `road_classes`); roads keep the provider's
    geometry (no simplification, no clipping) at six decimals like every
    published geometry; the road gray equals the page's `--rule` color;
    primary roads are drawn wider than secondary ones; the tract outline
    stays at EP-8a's `#555555` (darkening it to 3:1 against the roads would
    cost the boundary and the dark classes more than it gains);
    `SampleTransport` moved into `conftest.py` so the sample-built real
    zone can be a session fixture; the fixture screenshot was regenerated
    at the committed 1200 × 1600 size so the basemap note is in frame.
- **Unresolved risks / questions:** none new. For the M3 refinement gate:
  the routing network is OpenStreetMap, not these roads (the data card
  says so). For M6: the palette validation (CVD simulators) revisits the
  road gray and the outline together; road labels, water, and parks stay
  out of scope (ADR-0005 minimal basemap; PMTiles is OQ-F); the manual NVDA
  pass. For EP-10 (checkpoint 2): add the EP-5a … EP-8b rows to the
  estimate-accuracy table in `milestones.md`; the CI-samples README and
  DATA-LICENSES now name five sources.
- **No-go areas touched:** none (no PHI, no secret, nothing deployed,
  nothing under a `public/` zone or `site/dist/` committed, CI offline
  except GitHub + PyPI, no third-party request from the page; the CI
  sample is a US-public-domain subset with its status documented; the only
  prose claim added says the basemap is orientation and nothing is derived
  from it).
- `roadmap/README.md` packet row updated to `[x] 5cb5092`; the **M2
  heading closed** with the go/no-go evidence and the phase table's "First
  data" row marked done.
- **Exact next packet: the second checkpoint, EP-10** (the next free
  integer; fixture and real re-runs, docs and data-dictionary sync,
  license-label sweep, budgets, estimate accuracy including the EP-5a …
  EP-8b actuals, re-plan triggers), then the **M3 refinement gate** (apply
  the `milestones.md` carry-ins first).
