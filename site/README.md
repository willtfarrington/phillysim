# The slice page (EP-8a, EP-8b; the seed of the M6 site)

A static page that draws the public zone and nothing else: a MapLibre map of
the published tracts and facility points over the minimal public-domain
basemap (ADR-0005: the county boundary and, since EP-8b, the TIGER/Line
primary and secondary roads, grayscale), an HTML table of every published
column (the table-parity principle starts here), a data-vintage line, and an
attribution and license block, all read from `public/manifest.json` and the
files it registers. It is labeled **work in progress**, makes no claims, and
is **not deployed** (open question OQ-H in
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
that fails it (a zone from before public schema version 2 fails it, so a
stale `public/` has to be rebuilt by `phillysim run`); copies
`manifest.json`, `tracts.geojson`, `tracts.csv`, `sites.geojson`,
`sites.csv`, and `basemap.geojson` verbatim into `dist/data/` (digests
re-checked against the manifest; nothing is derived at build time since
EP-8b, the basemap being a gated public file like the rest); copies
`index.html`, `main.js`, `styles.css` and the vendored MapLibre into place;
and writes `dist/site.json` (site schema version 2, pipeline, every file's
SHA-256, the basemap's layer counts). The build is deterministic: the same
zone and sources give the same bytes. `--public DIR` builds from any
public-zone directory, `--out DIR` writes elsewhere (an existing target is
replaced only if it is a previous build).

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
| `basemap` | the layer counts in the basemap note under the legend; the layers themselves come from `basemap.geojson` (one `layer` property per feature) |

Nothing is fetched from any other host: the map library is vendored
([vendor/maplibre-gl/VENDOR.md](vendor/maplibre-gl/VENDOR.md), BSD-3-Clause,
digests recorded and tested), there are no tiles, fonts, or analytics, and
`tests/test_sitebuild.py` fails if a page source ever loads an absolute URL.

## The basemap and its contrast (EP-8b)

`data/basemap.geojson` is ADR-0005's minimal public-domain basemap as one
gated public file: the `county_boundary` layer (one polygon, the published
tracts dissolved) and the `roads` layer (TIGER/Line 2025 primary and
secondary roads, MTFCC S1100 / S1200; the [data
card](../docs/data-cards/tiger-roads.md)). The page draws them from one
GeoJSON source through filtered line layers, in this order from the bottom:
the map ground, the tract fills (80 % opaque), the **roads** (gray, 1.6 px
for primary and 1.0 px for secondary), the tract outlines, the **county
boundary**, the sites. A pipeline without a roads source (the fixture)
publishes a boundary-only file, and the page says so in the basemap note;
`document.documentElement.dataset.basemapLayers` names the layers it found,
which the browser tests read.

The roads sit **above** the fills, not beneath them as the EP-8b brief first
worded it: drawn beneath 80 %-opaque fills a road shows through at 1.25:1
against the lightest class (1.59:1 even if it were black), so no gray under
the fills can meet the spec. Above the fills the road gray is chosen against
the palette's lightest class, the map ground, the no-value gray, and the
county boundary, all at 3:1 or better (WCAG 2.2 non-text contrast, the
"meaningful boundaries" rule in the accessibility spec). The ratios below
are **measured from the constants in `main.js`** by
`tests/test_site_browser.py::test_road_gray_meets_the_contrast_spec_where_the_spec_binds`,
which fails if any required pair drops under 3:1 or the road gray changes
without this table.

| Pair | Colors | Ratio | Required |
|---|---|---|---|
| road vs lightest class (class 1) | `#767676` / `#fde725` | 3.60:1 | ≥ 3:1, met |
| road vs darkest class (class 5) | `#767676` / `#440154` | 3.35:1 | ≥ 3:1, met |
| road vs map ground | `#767676` / `#f5f5f5` | 4.17:1 | ≥ 3:1, met |
| road vs no-value gray | `#767676` / `#d9d9d9` | 3.22:1 | ≥ 3:1, met |
| road vs county boundary | `#767676` / `#1b1b1b` | 3.79:1 | ≥ 3:1, met |
| tract outline vs lightest class | `#555555` / `#fde725` | 5.91:1 | ≥ 3:1, met |
| county boundary vs lightest class | `#1b1b1b` / `#fde725` | 13.64:1 | ≥ 3:1, met |
| county boundary vs map ground | `#1b1b1b` / `#f5f5f5` | 15.80:1 | ≥ 3:1, met |
| road vs class 2 | `#767676` / `#5ec962` | 2.16:1 | recorded |
| road vs class 3 | `#767676` / `#21918c` | 1.19:1 | recorded |
| road vs class 4 | `#767676` / `#3b528b` | 1.67:1 | recorded |
| road vs tract outline | `#767676` / `#555555` | 1.64:1 | recorded |

The recorded rows are the limit of a single gray on a full-range sequential
palette: a gray that reads against both the lightest and the darkest class
is by construction close to the classes in the middle, and darkening the
tract outline to 3:1 against the roads would drop it to 1.2:1 against the
county boundary and the darkest classes. The roads are a reference layer
(orientation, never information), drawn under the meaningful boundaries and
named in the basemap note; the tract outline and the county boundary are
distinguished from the roads and from each other by width (0.6 px, 1.0 to
1.6 px, 1.8 px) and stacking order as well as by tone. The M6 palette
validation (CVD simulators, the manual NVDA pass) revisits the whole set.

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
downloaded) and asserts all of the above plus zero axe-core violations; since
EP-8b it also drives the page built from the real pipeline run on the
committed samples (48 roads in the basemap: both layers present, no error,
nothing off-origin, axe clean) and measures the contrast table above. CI
runs it on Windows and Linux and fails if no browser can be launched.

## Not here (M6)

The full Explore UI, detail panel, deep links, exports, road labels, water
and parks, hover tooltips, sorting and filtering, plain-language explainers
beyond the manifest descriptions, the PMTiles enhancement (OQ-F).
