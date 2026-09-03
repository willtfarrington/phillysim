# EP-8a — Minimal slice page: map + table from the public zone, county-boundary basemap, Playwright + axe

**Status:** [~] in progress · **Milestone:** M2 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-8 (2026-09-02, pickup pre-read; EP-8b is the other half)

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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated to `[x] <commit>`
- exact next packet: EP-8b
