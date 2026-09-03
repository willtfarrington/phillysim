# EP-8a — Minimal slice page: map + table from the public zone, county-boundary basemap, Playwright + axe

**Status:** [x] dd66884 (done 2026-09-03) · **Milestone:** M2 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-8 (2026-09-02, pickup pre-read; EP-8b is the other half)

## Outcome & value
The first page of the site, and the seed of M6 rather than a throwaway: a
static page (MapLibre GL JS, vendored; vanilla ES module; no framework, no
build tool) that renders the public zone's tracts and facility points over a
public-domain basemap whose first cut is the county boundary derived from
the published tract polygons, with an HTML table of every published column
(the table-parity principle starts here), a data-vintage line, and an
attribution and license block, all read from `public/manifest.json` and the
files it registers. A site build step turns a gated public zone into that
page, a local dev server serves it, and a browser test (Playwright + axe)
runs in CI against the fixture-built site. The page is labeled work in
progress, makes no claims, and is not deployed (OQ-H).

## Scope
- in: `site/` page sources; `phillysim.publish.sitebuild` (gate re-run,
  verbatim copy, county boundary, deterministic build) and `phillysim site
  build` / `site serve`; the vendored map library with recorded digests;
  Playwright + axe tests in CI; a committed screenshot; site README.
- out (explicit non-scope): the roads layer of the basemap and the contrast
  check against it (EP-8b); the full Explore UI, detail panel, deep links,
  exports, sorting, hover tooltips, plain-language explainers (M6);
  deployment (OQ-H).

## Prerequisites & locked decisions
- prerequisites: EP-7 (the public zone and the gate).
- locked decisions honored: ADR-0005 (minimal public-domain basemap; this
  packet's first cut is the boundary only); the accessibility spec in
  governance.md (table as the AT path, skip links, keyboard, focus, 24 px
  targets, reduced motion, 320 px reflow, color never sole carrier,
  CVD-safe five-class palette); the table-parity principle; build-time bins
  (the page never classifies); architecture.md "Static site" (MapLibre,
  plain GeoJSON, no third-party runtime calls, local dev server).
- dependencies: none at runtime. Tests use the machine's own Chrome or Edge
  through Playwright's `channel` option (no browser download), `playwright`
  and `axe-playwright-python` from PyPI in the dev group.

## Safety preconditions
Standing policy (EP-1). Packet-specific: no request leaves the page's own
origin (tested); attribution and license rendered from the manifest; the
page carries a work-in-progress note and states that nothing on it is an
access measure; `qa_only` columns render only under their description and
the manifest's QA note; the site build re-runs the publish gate and refuses
a failing zone; nothing under `site/dist/` or `data/public/` is committed;
the committed screenshot is of the synthetic fixture.

## Likely components & contracts (proposed)
`site/index.html`, `site/main.js`, `site/styles.css`, `site/README.md`,
`site/vendor/maplibre-gl/` (+ `VENDOR.md`);
`phillysim/src/phillysim/publish/sitebuild.py` (`build_site(public, out,
bounds=)` → `site.json`; `county_boundary`; `serve`); CLI group `site`
(`build`, `serve`); `tests/test_sitebuild.py`, `tests/test_site_browser.py`;
CI step `site build --fixture`; `docs/images/slice-page-fixture.png`.

## Implementation notes
Keep the page fed only from the public-zone artifacts (the parity mechanism
starts here): fields, bins, columns, sources, license, attribution, and the
QA note all come from the manifest. Vendor the map library rather than
adding a Node toolchain (ADR-0001's stack has one non-Python runtime, the
JVM, and it arrives at M3); mark the vendored directory `-text` so the
digests hold on every platform. The browser test must fail, not skip, in CI
when no browser can be launched.

## Acceptance criteria & evidence
- [x] Page renders map + table from public-zone artifacts fully offline
  (every request stays on the dev server's origin; asserted).
- [x] axe: no violations; keyboard reaches all controls (asserted in the
  browser test, on Windows and Linux in CI).
- [x] Site build deterministic, gated, verbatim (asserted).
- Evidence: CI green with the Playwright + axe module; screenshot
  `docs/images/slice-page-fixture.png` (own work, synthetic data).

## Tests / validation
`uv run pytest tests/test_sitebuild.py tests/test_site_browser.py`;
`uv run phillysim site build --fixture && uv run phillysim site serve` and
look; CI.

## Resource budget
Trivial (the vendored library is 1.2 MB in the repository; the browser tests
add about ten seconds to the suite).

## Risks, rollback, stop condition
UI scope creep: anything beyond render + table + vintage + attribution
belongs to M6; stop there. A CI runner without a launchable Chrome or Edge
would fail the suite: the fallback is a SHA-pinned browser install step,
which changes the CI host policy and is an owner decision.

## Documentation / ADR updates
`site/README.md`; `phillysim/README.md` (layout, commands); root README;
`roadmap/{README,quality,architecture,open-questions}.md`; CHANGELOG;
screenshot.

## Handoff payload (filled 2026-09-03)
- **Packet:** EP-8a — done at commit `dd66884` (+ this status commit).
  Planning Baseline v1.0. The pickup pre-read split EP-8 (see
  [EP-8](EP-8-slice-page.md)); this half fit one session. CI run
  [33708373447](https://github.com/willtfarrington/phillysim/actions/runs/33708373447)
  on `dd66884` green on `windows-latest` and `ubuntu-latest` (pytest with
  the new browser module driving the runner's own Chrome, ruff, the four
  fixture-pipeline steps, `gate --fixture`, and the new `site build
  --fixture` step; no browser download, CI hosts unchanged).
- **Files changed:** new `site/{index.html,main.js,styles.css,README.md}`,
  `site/vendor/maplibre-gl/{maplibre-gl.mjs,maplibre-gl-shared.mjs,
  maplibre-gl-worker.mjs,maplibre-gl.css,LICENSE.txt,VENDOR.md}`,
  `phillysim/src/phillysim/publish/sitebuild.py`,
  `phillysim/tests/{test_sitebuild,test_site_browser}.py`,
  `docs/images/slice-page-fixture.png`, `.gitattributes`,
  `roadmap/EP-8a-slice-page.md`, `roadmap/EP-8b-basemap-roads.md`; changed
  `cli.py` (`site build` / `site serve`), `tests/conftest.py` (session
  fixtures `fixture_public_zone` / `built_site`; loopback allowed by the
  no-network guard), `pyproject.toml` + `uv.lock` (dev: `playwright`,
  `axe-playwright-python`), `.pre-commit-config.yaml` (vendor excluded),
  `.github/workflows/ci.yml`, `docs/data-dictionary.md`, `phillysim/README.md`,
  `README.md`, `CHANGELOG.md`, `roadmap/{README,architecture,quality,
  open-questions,EP-8-slice-page}.md`.
- **Commands/tests run + results.** `uv run pytest` → 423 passed, 2
  skipped (real-spine tests; 400 before the packet) in about 25 s; `ruff
  check` / `ruff format --check` clean; `pre-commit run --all-files` all
  hooks passed; staged diff scanned for usernames / absolute paths → none;
  vendored bytes in the index equal the digests in `VENDOR.md` (checked
  with `git show :path | sha256sum`). `phillysim site build --fixture` →
  gate green, five files verbatim, `basemap.geojson` derived, `site.json`
  written; `site build` on the real zone (working clone, scratch output,
  deleted afterwards) → 408 tracts and 164 sites rendered, the QA column
  under its description with the manifest's QA note shown, axe zero
  violations, keyboard order identical to the fixture page; the real-data
  screenshot was not committed. Headless smoke in the machine's Chrome
  (152) and Edge: `data-map="ready"`, no console errors, no request off the
  dev server's origin. **The page, as measured:** legend classes from the
  manifest's edges; tab order skip link → column select → map canvas →
  zoom in → zoom out → skip-past-map link → two scrollable table regions →
  footer links; controls 32 × 32 px (zoom) and ≥ 36 px tall (select); 320
  px viewport: document scroll width equals client width after
  `overflow-wrap: anywhere` (the long column slugs overflowed first);
  without WebGL the page reports it and the tables stand.
- **Resource observations:** one session, at the S estimate. Vendored
  library 1.2 MB in the repository; browser tests add about 12 s to the
  suite; the site build takes well under a second; the fixture site is
  about 1.3 MB on disk, the real one about 2.2 MB (`tracts.geojson` 876 KB
  dominates, as EP-7 measured). CI about 2 min per platform.
- **Decisions made (owner-reviewed 2026-09-03, all four recommended options
  accepted):**
  - **Commit, push, CI, handoff:** done as above.
  - **EP-8 split confirmed** (EP-8a page; EP-8b TIGER major roads for the
    basemap, M2 closes with it).
  - **OQ-H: not deployed.** Recorded in open-questions.md; revisited at M7
    with the Pages deploy. Nothing under `site/dist/` or `data/public/` is
    committed.
  - **Site stack:** MapLibre GL JS 6.7.0 vendored with recorded digests
    (BSD-3-Clause; upgrade recipe in `VENDOR.md`; Dependabot cannot track
    it) rather than a Node toolchain; browser tests through PyPI
    `playwright` + `axe-playwright-python` driving the machine's own
    Chrome/Edge (`channel`), so CI downloads no browser and the host policy
    stays GitHub + PyPI; the test-suite no-network guard allows loopback
    only.
  - Routine (agent's call, logged): the site build re-runs the publish
    gate rather than trusting the installed zone; the county boundary is
    derived at site-build time from the published tract polygons and
    carries the tract file's label in-file (EP-8b moves the basemap into
    the public zone with the roads, as a public-schema bump); the page's
    palette is five viridis samples pending the M6 CVD validation; the
    map's attribution control carries the manifest's attribution; the
    sites table is included (parity for the points, not only the tracts);
    `qa_only` columns render as options marked "(QA only)" with the
    manifest's QA note under the description (the brief allowed "not at
    all"; showing them under the note keeps the parity mechanism honest and
    the real zone would otherwise be empty); a `--data-root` with
    `--fixture` names the fixture root directly (existing CLI behaviour,
    relied on by the session fixture); the committed screenshot is of the
    synthetic fixture.
- **Unresolved risks / questions:** none new. Noted for EP-8b: the roads
  layer needs a new raw source and a public-schema bump (the runner will
  not re-run `publish` on a code-only change); the contrast ratios against
  the road gray must be measured and written into the site README; the
  page expects `basemap.geojson` with a `layer` property per feature. For
  M6: the CVD validation of the palette, hover/click detail panel, sorting,
  plain-language explainers, the manual NVDA pass.
- **No-go areas touched:** none (no PHI, no secret, nothing deployed,
  nothing under a `public/` zone or `site/dist/` committed, CI offline
  except GitHub + PyPI, no third-party request from the page; the only
  prose claims added say the page is work in progress and that nothing on
  it is an access measure).
- `roadmap/README.md` packet row updated to `[x] dd66884`; the M2 heading
  stays open (EP-8b remains).
- **Exact next packet: EP-8b** ([EP-8b-basemap-roads.md](EP-8b-basemap-roads.md));
  after it, the second checkpoint (next free integer), then the M3
  refinement gate.
