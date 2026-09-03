# EP-8b — Basemap roads: TIGER major-roads source, roads layer, contrast check; M2 closes

**Status:** [ ] planned · **Milestone:** M2 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-8 (2026-09-02, pickup pre-read; EP-8a is the other half)

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
- [ ] Roads acquired, validated, curated, published, gated, and drawn;
  fresh-clone run reproduces the zone byte for byte (digests recorded).
- [ ] Contrast ratios recorded and within spec; axe and the browser tests
  stay green.
- [ ] M2 go/no-go recorded: slice reproducible from a fresh clone, license
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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated to `[x] <commit>` and the M2
  heading closed with the go/no-go evidence
- exact next packet: the second checkpoint (next free integer), then the
  M3 refinement gate
