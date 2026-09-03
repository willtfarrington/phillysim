# EP-7 — Thin-slice metric + public zone + license bucketing

**Status:** [x] bf9df7f (done 2026-09-02; pickup pre-read: fit one session, not split) · **Milestone:** M2 · **Effort:** M (1–2 sessions, medium confidence) · **Parallel with:** —

## Outcome & value
The deliberately trivial slice metric — straight-line QA distance from tract
centroid to nearest supermarket-format point, **labeled QA-only, never a
published access measure** — flowing curated → public zone with
license-bucket labeling (this table is Bucket A until OSM enters at M3+),
build-time bin computation, and the publish-gate check (license labels,
bounds, no raw-path leakage). Proves the public-boundary machinery
end-to-end.

## Scope
- in: slice metric, bucket labeling, publish gate, public GeoJSON/CSV.
- out (explicit non-scope): real travel times (M3); site UI beyond EP-8's
  minimal page.

## Prerequisites & locked decisions
- prerequisites: EP-6.
- locked decisions honored: AM-1 / ADR-0003 bucket rules; the analytic schema
  contract; build-time bins.
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the public zone contains only
tract-level aggregates + facility points already public upstream; the publish
gate must be green before anything leaves curated.

## Likely components & contracts (proposed)
`src/phillysim/metrics/slice.py`; `src/phillysim/publish/{bucket,gate}.py`;
`data/public/` outputs (gitignored; artifacts only).

## Implementation notes
The publish gate is the reusable artifact here; the metric exists to prove
the plumbing and will be retained only as a QA column.

## Acceptance criteria & evidence
- [x] Publish gate blocks an intentionally mislabeled file (negative test:
  `tests/test_publish.py::test_gate_blocks_an_intentionally_mislabeled_file`,
  a file labeled Bucket A whose sources require Bucket B; plus one negative
  per gate check, and the stage-level refusal to install a rejected zone).
- [x] Public GeoJSON/CSV validate against schema + bucket rules (the gate is
  green on the fixture's zone in the suite and as a CI step, and on the
  real zone locally and from a fresh clone; public schema v1 in the data
  dictionary).
- Evidence: golden metric test (`tests/test_slice_metric.py`: hand-computed
  distances, brute-force check on the samples); gate negative tests;
  fixture and real-pipeline integration (`tests/integration/`).

## Tests / validation
Golden metric test; gate negative test; integration on fixture.

## Resource budget
Trivial.

## Risks, rollback, stop condition
Temptation to publish the QA metric as an access measure — prohibited; stop
and re-read methodology.md if it comes up.

## Documentation / ADR updates
Data dictionary (public schema v1).

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-7 — done at commit `bf9df7f` (+ this status commit).
  Planning Baseline v1.0. Pickup pre-read judged the M-sized packet to fit
  one session (the runner, spine, SNAP layer, contracts, and sample
  machinery all existed; the new work is one metric module, one publish
  package, and docs), so it was not split; it did fit. CI run
  [33704489049](https://github.com/willtfarrington/phillysim/actions/runs/33704489049)
  on `bf9df7f` green on `windows-latest` and `ubuntu-latest` (pytest, ruff,
  the three fixture-pipeline steps, and the new `phillysim gate --fixture`
  step; CI never runs the real pipeline).
- **Files changed:** new `phillysim/src/phillysim/metrics/{__init__,slice}.py`,
  `publish/{__init__,bucket,bins,export,gate}.py`,
  `tests/{test_publish,test_slice_metric}.py`,
  `docs/method-cards/qa-straight-line.md`; changed `adapters/base.py`
  (`Adapter.citation`) and the four adapters (citations), `pipeline.py`
  (`metrics` + `publish` stages, `PUBLISH_SOURCES`), `fixtures/pipeline.py`
  (`publish` body replaced; `FIXTURE_BOUNDS`, descriptions), `stages.py`
  (`Pipeline.upstream_raw`), `cli.py` (`gate` verb),
  `tests/integration/test_{fixture,real}_pipeline.py`,
  `tests/fixtures/tinycity/README.md`, `.github/workflows/ci.yml`,
  `.gitignore` (`data/public/`), `docs/data-dictionary.md` ("Public zone"
  section replaces the placeholder export; analytic-table instances; CRS
  row; intermediate row), `docs/DATA-LICENSES.md` ("How labels are
  applied"; labeling status), `docs/CLAIMS.md` ("Mechanical enforcement"),
  `docs/data-cards/README.md`, `docs/method-cards/store-formats.md`,
  `roadmap/{architecture,quality,sources,milestones}.md` (stage rows 10–11;
  test-matrix rows; gate note; M5/M6 carry-in), `README.md`,
  `phillysim/README.md` (layout, public-zone section, baselines),
  `CHANGELOG.md`, `roadmap/README.md` (packet row), this file.
- **Commands/tests run + results.** Working clone: `uv run pytest` → 400
  passed, 2 skipped (real-spine tests; 358 before the packet); `ruff check`
  / `ruff format --check` clean; `pre-commit run --all-files` all hooks
  passed; staged diff scanned for usernames / absolute paths → none;
  `pytest tests/test_spine_invariants.py tests/test_slice_metric.py
  --real-data-root ../data` 24 passed. **Real run, working clone
  (`data/`):** `phillysim run` skipped the five fresh stages and ran
  `metrics` (0.1 s) and `publish` (0.3 s); `gate` green (4 files Bucket A /
  CC-BY-4.0, 3 sources, 408 tracts, 164 sites); `status` 7 fresh; `verify`
  4 of 4 snapshots, 7 of 7 stages; after the `public_schema_version`
  parameter was added `publish` re-ran as stale on parameters (0.4 s) with
  identical file content except the bin-edge rounding. **Fresh-clone
  rehearsal of `bf9df7f`** (scratch directory, `git clone -c
  core.longpaths=true` from GitHub, deleted afterwards): `uv sync --locked`
  7 s; `uv run pytest` 400 passed, 2 skipped (17.8 s); `phillysim run`
  acquired all four sources (11.4 s incl. 121 MB), validate 3.1 s, spine
  0.2 s, demographics 0.8 s, snap_retailers 2.4 s, metrics 0.0 s, publish
  0.3 s (about 19 s wall); second `run` 0 ran / 7 skipped; `status` 7
  fresh; `verify` 7 of 7; `gate` green; `git status` clean; data root
  118 MB. **Reproducibility reference (byte-identical between the working
  clone and the fresh clone):** `public/manifest.json` sha256
  `b22e28248a7ee475e91a972119d2bf10c000f0b1fc70f2a9769b08e88cbf89dc`,
  `public/tracts.geojson` `30741eac8684c8b671c45af3db7b65ac03be4e6e86e951ea6b1a1204b9ab300a`
  (875,546 bytes; 176 KB gzipped), `public/tracts.csv`
  `ce380762dcdaf00ec03eaf9c50af30b64525cc95014eef547ccd5cdb412d5ce5`,
  `public/sites.geojson` `45a437578adcdfa51bbe70fc4c52b72b855f026f4d99be17a865ca3618f9a3d3`,
  `public/sites.csv` `ea3bdea90b8795421ff89940d5da5fac9765e3cf2b0f0debc8087fab3effa1a3`,
  `curated/tract_metrics.parquet`
  `fa8b8bdd38f8a5b4c9ea7f9758f9040c7d4a976e9a798e8531f17a4fb5c4b9ce`;
  spine and SNAP-layer digests unchanged from EP-5b / EP-6. **M2 go/no-go
  evidence:** the slice is reproducible from a fresh clone and the license
  buckets are applied and gated; the milestone closes with EP-8's page.
- **The metric, as measured (QA only):** 408 tracts, 164 supermarket-format
  destinations, no null distance; population-weighted center to the nearest
  supermarket-format retailer: min 35.3 m, median 622.5 m, max 3,150.6 m;
  quintile edges 35.3 / 355.5 / 544.14 / 767.98 / 1,047.02 / 3,150.6 m.
  Recorded in the method card; **not an access measure** and never to be
  presented as one (the manifest flags it, the gate enforces the flag).
- **Resource observations:** one session (the fifth M packet in a row to
  land at the estimate's low end); stages under 0.5 s; public zone 965 KB;
  suite 400 tests in about 15 s; network 121 MB for a fresh clone.
- **Decisions made (owner-reviewed 2026-09-02, all recommended options
  accepted):**
  - **Commit, push, CI, fresh-clone rehearsal, handoff:** done as above.
  - **`data/public/` is gitignored until a release.** `git add -A` staged
    the real public zone during the session because that zone was the one
    not ignored; it was unstaged, never committed, and the ignore line
    added with a comment (a release adds the files deliberately with
    `git add -f`). Consistent with this brief's "gitignored; artifacts
    only" and the release checklist.
  - **Facility points with store names stay in the public zone**
    (`sites.geojson` / `sites.csv`: the 164 supermarket-format retailers,
    provider-public facility data, covered by the delisting policy; CSV
    escaping exercised on real provider text). Nothing is deployed before
    M7.
  - Routine (agent's call, logged): the real `metrics` stage carries the
    architecture's stage name and the locked analytic shape with the QA
    metric as its only row type (`methods_version` `slice-qa-1`; M5
    replaces the body, carry-in recorded); a `qa_` ID prefix, a manifest
    `qa_only` flag with a QA note, and a gate rule make the QA-only status
    machine-checked rather than promised; buckets are derived from the raw
    manifests (Bucket B contagious) and the fixture zone is therefore
    Bucket B, which gives CI an ODbL-path check for free; the `publish`
    stage's single output is the whole `public/` directory so the runner
    installs it atomically and a gate failure leaves nothing; the public
    manifest is the CSV sidecar and GeoJSON carries the label in-file;
    quintile bins with edges recorded in the manifest; `public_schema_version`
    is a stage parameter (fingerprints never include code, so a shape
    change must bump it to re-run `publish`: found when the scratch
    fixture root skipped `publish` after a code fix); a `gate` verb rather
    than folding the gate into `verify`; ACS is not among the published
    sources yet (nothing published derives from it); adapters gained a
    `citation` for attribution.
- **Unresolved risks / questions:** none new. Noted for EP-8: the page must
  read fields, bins, columns, license, attribution, and the QA note from
  `public/manifest.json` and render `qa_only` fields only under their
  description (or not at all); OQ-H (deploy the work-in-progress page?)
  defaults to not deployed. The ODbL notice sentence in `bucket.py` is
  project wording that no published file carries yet (the real zone is
  Bucket A); it gets a legal-review flag with the site's export UI at M6.
- **No-go areas touched:** none (no PHI, no secret, nothing under a tracked
  `public/` zone, the data zones gitignored, CI offline; the only prose
  claim added is that the slice metric is *not* an access measure).
- `roadmap/README.md` packet row updated to `[x] bf9df7f`; the M2 heading
  stays open (EP-8 remains).
- **Exact next packet: EP-8** (minimal slice page; M-sized, so read at
  pickup and split before work starts if it will not fit one session).
