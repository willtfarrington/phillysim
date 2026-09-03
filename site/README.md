# The slice page (EP-8a; the seed of the M6 site)

A static page that draws the public zone and nothing else: a MapLibre map of
the published tracts and facility points over the county boundary, an HTML
table of every published column (the table-parity principle starts here), a
data-vintage line, and an attribution and license block, all read from
`public/manifest.json` and the files it registers. It is labeled **work in
progress**, makes no claims, and is **not deployed** (open question OQ-H in
[roadmap/open-questions.md](../roadmap/open-questions.md) defaults to not
deployed until the M7 release gates).

![The slice page built from the tinycity fixture: work-in-progress banner,
column selector, map with legend, tract table](../docs/images/slice-page-fixture.png)

## Build and serve

```
cd phillysim
uv run phillysim run --fixture            # or `phillysim run` for the real slice (network once)
uv run phillysim site build --fixture     # -> site/dist/ (gitignored), from data/fixture/public/
uv run phillysim site build               # from data/public/ (the real slice)
uv run phillysim site serve               # http://127.0.0.1:8000/ until Ctrl-C
```

`site build` re-runs the publish gate on the zone first and refuses a zone
that fails it; copies `manifest.json`, `tracts.geojson`, `tracts.csv`,
`sites.geojson`, `sites.csv` verbatim into `dist/data/` (digests re-checked
against the manifest); derives `dist/data/basemap.geojson`, the county
boundary as the union of the published tract polygons (labeled in-file with
the tract file's license and attribution, since it derives from nothing
else); copies `index.html`, `main.js`, `styles.css` and the vendored MapLibre
into place; and writes `dist/site.json` (schema version, pipeline, every
file's SHA-256). The build is deterministic: the same zone and sources give
the same bytes. `--public DIR` builds from any public-zone directory,
`--out DIR` writes elsewhere (an existing target is replaced only if it is a
previous build).

`site serve` is the standard library's threaded HTTP server bound to loopback
with the MIME types ES modules and GeoJSON need; it exists because module
scripts require an `http://` origin. It is a dev server, not hosting.

## What the page reads and how it renders it

| Manifest member | Rendered as |
|---|---|
| `fields` | the column selector (one option per published metric column, `(QA only)` appended where `qa_only`); the description under the selector; the "Columns" definition list |
| `qa_note` | the highlighted note under the selector whenever the selected column is `qa_only` |
| `bins` | the legend (class ranges from the recorded edges) and the map fill (`<column>_bin` matched to a five-class sequential palette, sampled evenly when a column has fewer classes; grey for no value). The page never classifies on its own |
| `columns` | the header rows of the tracts and sites tables, in the file's order |
| `sources` | the data-vintage line: source, snapshot ID, synthetic flag, citation |
| `license`, `attribution` | the attribution block and the map's attribution control |
| `files` | the download list with row and byte counts |
| `bounds` | the initial view and the pan limit |

Nothing is fetched from any other host: the map library is vendored
([vendor/maplibre-gl/VENDOR.md](vendor/maplibre-gl/VENDOR.md), BSD-3-Clause,
digests recorded and tested), there are no tiles, fonts, or analytics, and
`tests/test_sitebuild.py` fails if a page source ever loads an absolute URL.

## Accessibility (the spec in roadmap/governance.md)

The table is the assistive-technology path; the map (a canvas) is an
alternative view of the same values. Skip links before and after the map;
every control keyboard-reachable in document order (selector, map canvas
with MapLibre's arrow-key handler, zoom buttons, the scrollable table
regions); visible focus rings at 3:1; controls at or above 24 CSS px; text
at or above 4.5:1 on a muted grayscale chrome; `prefers-reduced-motion`
honored (no animated fit, no transitions); reflow to 320 CSS px with the
tables scrolling in their own containers; color never the sole carrier
(legend ranges, table values, class number in the status line on click).
Without WebGL the page says so and the tables stand.

`tests/test_site_browser.py` drives the fixture-built page in the machine's
own Chrome or Edge through Playwright (the `channel` option, so nothing is
downloaded) and asserts all of the above plus zero axe-core violations; CI
runs it on Windows and Linux and fails if no browser can be launched.

## Not here (M6)

The full Explore UI, detail panel, deep links, exports, the roads layer of
the basemap (EP-8b), hover tooltips, sorting and filtering, plain-language
explainers beyond the manifest descriptions, the PMTiles enhancement.
