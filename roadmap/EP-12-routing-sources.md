# EP-12 — Routing sources: OSM extract (Geofabrik, Bucket B) and SEPTA GTFS through the guarded path

**Status:** [~] in progress (work done 2026-09-03; owner review and commit pending) · **Milestone:** M3 · **Effort:** S (1 session, medium confidence) · **Parallel with:** —

## Outcome & value
The two sources the routing spike needs exist as real snapshots in the raw
zone, acquired through the guarded path like the five sources before them
and nothing else: the Pennsylvania OpenStreetMap extract from Geofabrik
(ODbL; **the first Bucket B source of the real pipeline**) and SEPTA's GTFS
feed pinned to a release tag (custom terms; never republished). Each has an
adapter, allowlist, guard limits sized for files of hundreds of megabytes,
terms page archived and sentence-checked, contract, data card,
DATA-LICENSES record, and CI sample. The OSM adapter also clips the state
extract to the county and a buffer, so the toolchain packet that follows
(EP-13) has a network to smoke-test the JVM on. The pipeline's single
`SNAPSHOT_ID` becomes per-source, so the five `2026-09-02` snapshots stay as
they are and the two new sources take their own acquisition date. No
routing runs here; the JVM is EP-13's.

## Scope
- in:
  1. **Per-source snapshot IDs** (owner decision at EP-11, question 5:
     option A). `phillysim.pipeline.SNAPSHOT_ID` becomes a mapping
     `SNAPSHOT_IDS = {source: id}`; the five existing sources keep
     `2026-09-02`, `osm_network` and `gtfs` take the date of their first
     acquisition; `RAW_SNAPSHOTS` and `_raw()` derive from the mapping; the
     `acquire` stage's `snapshot_id` parameter becomes `snapshot_ids` (a
     parameter change re-runs `acquire`, which re-uses the five verified
     snapshots and fetches only the new ones). Every document that names the
     constant (`phillysim/README.md`, the five data cards, the data
     dictionary) is updated in the same commit.
  2. **`osm_network` adapter** (`phillysim.adapters.osm`; the source name is
     the fixture's, so the architecture stage table holds for both
     pipelines). Acquires the **dated** Geofabrik extract
     `https://download.geofabrik.de/north-america/us/pennsylvania-260831.osm.pbf`
     (345,912,530 bytes; provider MD5 `a779d2ef14c8addce6eac207ab9cd851`
     from the sibling `.md5` file, checked at acquisition in addition to the
     manifest's SHA-256; data current to 2026-09-02T20:20:51Z), **stored as
     delivered**; never the `-latest` file (its bytes change daily). Terms
     page in force: the Geofabrik region page
     `https://download.geofabrik.de/north-america/us/pennsylvania.html`,
     archived as `terms.html`, checked for the sentence "created by
     OpenStreetMap Contributors" and the phrase "License: ODbL". Allowlist:
     `download.geofabrik.de` only. Guard limits: 1 GiB file cap (the file
     is not an archive: no member or ratio guard applies; `inspect_zip` is
     not called on a PBF). Manifest `license_bucket = "B"`; `license_note`
     names ODbL 1.0, OpenStreetMap contributors, Geofabrik as processor,
     and the extract date. **Read** = the clip: `read(snapshot_dir,
     target)` writes `pennsylvania-260831-philadelphia-5km.osm.pbf` under
     the caller's path (the `network` stage's staging, installed to
     `intermediate/network/`), the extract clipped to the county bounds
     (`adapters.base.COUNTY_BOUNDS`) buffered by 5 km, with **pyosmium**
     (`osmium` 4.3.1, wheels for Windows and Linux on Python 3.13,
     resolved 2026-09-03 with `uv pip compile --only-binary :all:`), the
     way-complete strategy (every way that touches the box, with all its
     nodes), deterministic output (sorted, no metadata). The clip is a
     derived file, Bucket B by derivation, fingerprinted by the stage that
     writes it; the state extract stays byte-for-byte in `raw/`. The
     contract checks the clipped file: a valid PBF header, node and way
     counts within a recorded band, every node inside the buffered box,
     `highway` ways present.
  3. **`gtfs` adapter** (`phillysim.adapters.septa_gtfs`). Acquires
     `https://github.com/septadev/GTFS/releases/download/v202609060/gtfs_public.zip`
     (21,555,258 bytes; SHA-256
     `4d3fa20ea094937a9bb6389ad52017e1ac90a564aee497f318797e1b1e4f07ab`
     as GitHub records it; release published 2026-09-02T15:48:11Z, "Summer
     RR, Fall Bus-Metro, Sept Adjustments"), stored as delivered: one zip
     holding `google_bus.zip` and `google_rail.zip`. Bus/Metro feed
     authoritative 2026-09-06 through 2027-02-20; Regional Rail
     authoritative 2026-09-06 through 2026-10-17 (the release notes). The
     pinned analysis dates (ADR-0008) lie inside both windows. Allowlist:
     `github.com` and `objects.githubusercontent.com` (the release-asset
     redirect target). Terms page in force: SEPTA's developer page
     `https://www3.septa.org/developer/` (the license agreement, last
     updated 2014-03-18 by its own text), archived as `terms.html` and
     checked for the sentences "SEPTA reserves the right to alter and/or
     no longer provide the Trip Planning Data at any time without prior
     notice." and "SEPTA reserves the right to institute a license fee at
     any time in the future without prior notice."; a change is the stop
     condition (quarantine kind `terms`, nothing admitted). Guard limits:
     128 MiB file cap, 1 GiB extracted, ratio 50, 50 members, applied to
     the outer zip at acquisition and to each inner zip by the reader.
     Manifest `license_bucket = "A"` (the feed is not OSM-derived;
     Bucket B never comes from it) with a `license_note` stating SEPTA's
     terms (revocable, no fee today but reservable, no alteration or
     commercial use of SEPTA's marks) and the project's position: computed
     travel times are facts, no feed contents are ever published, the raw
     feed is never redistributed (sources.md, DATA-LICENSES). **Read** =
     unwrap without expanding: `read(snapshot_dir, target)` runs the zip
     guards on each inner zip and copies `google_bus.zip` and
     `google_rail.zip` as files into the caller's path (R5 reads GTFS
     zips directly, so nothing inside them is extracted); the contract
     checks each inner feed's required GTFS files and columns, its
     `feed_info.txt` dates (the pinned Wednesday and Saturday inside the
     authoritative window of both feeds), and that every stop lies inside
     the buffered county box or is flagged as outside (a count, not a
     failure: SEPTA serves the suburbs).
  4. **Data cards, DATA-LICENSES, dictionary, sources.md.**
     `docs/data-cards/osm-network.md` and `septa-gtfs.md` in the existing
     card shape (contributes, provider and file, vintage, terms and bucket,
     coverage and filter, limits, claims rows), the index row for each;
     two dated snapshot records in `docs/DATA-LICENSES.md` (the OSM one is
     the first Bucket B record; the SEPTA one records the click-through
     agreement text as archived, that the project accepts those terms, and
     the facts-not-contents position); `docs/data-dictionary.md` gains the
     two raw-source sections and the `intermediate/network/` entries;
     `roadmap/sources.md` rows gain "acquired" with the date.
  5. **CI samples.** `tests/fixtures/spine-samples/raw/osm_network/<id>/`:
     a PBF clipped to the six sample tracts (a few hundred kilobytes),
     real OSM data under ODbL with the required notice in the samples
     README and a Bucket B manifest (`synthetic: false`), cut by
     `build_samples.py` from the real snapshot. `raw/gtfs/<id>/`: a
     **synthetic** feed in SEPTA's layout (an outer zip with two inner
     zips, a handful of stops and trips over the sample tracts, valid
     `feed_info.txt` dates), `synthetic: true`, because committing any
     subset of the real feed would republish feed contents. The contract
     tests (`tests/contracts/test_osm_network.py`, `test_septa_gtfs.py`)
     and the real pipeline's integration test run on them offline; the
     integration test's `acquire` covers the per-source IDs.
  6. **`network` stage** in the real pipeline (`phillysim.network`,
     between `basemap` and `metrics`, inputs the two snapshots and the
     spine; outputs `intermediate/network/` holding the clipped PBF and the
     two GTFS zips, plus `intermediate/network.json` with the counts):
     the stage body is the two adapters' reads and a summary. It reads no
     JVM; the smoke route on its output is EP-13's.
- out (explicit non-scope): installing the JDK or the R5 jar, r5py in the
  lock, any JVM run (EP-13); the run matrix (EP-14); the verdict (EP-15);
  a City source (M4); publishing anything (the public zone stays Bucket A:
  `PUBLISH_SOURCES` is unchanged and nothing downstream of `network`
  reaches `publish` in this packet); a controlled refresh of the five
  existing snapshots.

## Prerequisites & locked decisions
- prerequisites: EP-11 (this gate), EP-10, M2 done.
- locked decisions honored: ADR-0003 (OSM-derived content is Bucket B and
  contagious; the gate enforces it and the fixture zone exercises it);
  ADR-0006 (a snapshot ID per source is the dataset version axis;
  architecture.md "Zones & identifiers" already says "date-stamped
  per-source identifier"); ADR-0007 (the clip box is computed from the
  county bounds in the analysis CRS and expressed in WGS 84 for pyosmium);
  ADR-0008 (the extract, the release tag, the clip extent, the pinned
  dates); the download-path order and the terms-archive stop condition
  (EP-5a); sources.md (pin SEPTA release tags, never republish the feed,
  re-read the terms at every refresh); docs/CLAIMS.md wording in every
  card and note; the raw zone is immutable (nothing is written beside a
  raw file: the clip and the unwrapped zips land in `intermediate/`).
- dependencies: `download.geofabrik.de` (about 346 MB); `github.com` and
  `objects.githubusercontent.com` (21.6 MB); `www3.septa.org` (the terms
  page); PyPI for `osmium` (a runtime dependency added to the locked
  stack; wheels on both platforms; the dependency policy test stays green:
  nothing in its tree is `GDAL` or `fiona`).

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the OSM extract and the GTFS
feed enter `raw/` only through the guarded path (allowlists as above, caps
sized as above, the PBF never treated as an archive, the outer zip
inspected before anything is copied out of it, terms archived and
sentence-checked); the GTFS feed and anything unwrapped from it are never
copied under `public/` or `site/`, and no GTFS row is committed to the
repository (the CI sample is synthetic); every file carrying a value
computed over the OSM network is Bucket B by derivation, never by hand
(the clipped PBF's provenance is the `osm_network` snapshot and the
`network` stage records it); the OSM CI sample is committed only with the
ODbL notice and "© OpenStreetMap contributors" in the samples README and
its manifest; the terms-page sentence for each provider is quoted verbatim
in the adapter and in DATA-LICENSES; CI stays offline; no machine
identifier or absolute path enters a tracked file (the samples builder and
the stage report scrub the data root); the dependency policy test runs on
the new lock.

## Likely components & contracts (proposed)
`src/phillysim/adapters/osm.py`, `adapters/septa_gtfs.py`,
`adapters/__init__.py` (registry), `src/phillysim/network.py` (the stage),
`src/phillysim/pipeline.py` (`SNAPSHOT_IDS`, the `network` stage,
`acquire` parameter `snapshot_ids`), `pyproject.toml` + `uv.lock`
(`osmium`), `tests/contracts/test_osm_network.py`,
`tests/contracts/test_septa_gtfs.py`, `tests/test_network.py`,
`tests/integration/test_real_pipeline.py` (nine stages),
`tests/fixtures/spine-samples/` (two sample snapshots, README,
`build_samples.py`), `docs/data-cards/{osm-network,septa-gtfs,README}.md`,
`docs/DATA-LICENSES.md`, `docs/data-dictionary.md`, `phillysim/README.md`,
`roadmap/architecture.md` (stage table row 8 gets its real logic),
`roadmap/sources.md`, `CHANGELOG.md`, this file. Contracts: manifest
fields as the dictionary fixes them; the `network` stage's outputs are
`intermediate/network/` (a directory output, like `public/`) and
`intermediate/network.json`.

## Implementation notes
Follow EP-5a and EP-8b for the adapter shape (`SnapshotSpec`, `Fetch`,
`Limits`, `read`, `filter_note`, `citation`); the terms phrases are the
verbatim sentences above. The PBF is the first non-archive large file:
`acquire_snapshot` must skip `inspect_zip` for it (branch on the file
name's suffix, tested). The Geofabrik MD5 is a second, provider-side
check: fetch the `.md5` file through the same path and compare before
admission; a mismatch is a stop. pyosmium's clip: read the state extract
with a bounding-box filter and write with `osmium.SimpleWriter`, keeping
every way that has a node inside the box with all of its nodes (R5 needs
complete ways); confirm the output opens in pyosmium and record node and
way counts in `network.json`; the sample builder uses the same function
on the six-tract box. The GTFS reader never opens `stops.txt` from the
real feed in CI (the sample is synthetic); the contract reads column
headers and `feed_info.txt` from each inner zip in place. Keep the count
of stops outside the buffered box as information. Register the stage
with `params={"buffer_m": 5000, "crs": ANALYSIS_CRS}` so a change of
extent re-runs it. Record the acquisition's console output (bytes,
seconds, attempts) for the handoff, as every source packet has.

## Acceptance criteria & evidence
- [ ] `phillysim run --stage network` on the existing data root acquires
      the two new snapshots (the five existing ones re-used, not
      re-downloaded), admits them with their terms pages, and writes
      `intermediate/network/` with the clipped PBF and the two GTFS zips
      and `intermediate/network.json`; `verify` passes (7 of 7 snapshots,
      9 of 9 stages); a second `run` skips everything; the public zone is
      unchanged (digests equal the EP-8b references; still Bucket A).
- [ ] Both manifests carry `terms_archive`, the right bucket, and a
      `license_note`; the OSM manifest is the first real Bucket B manifest
      and `derive_bucket` over a source list containing it returns B
      (asserted).
- [ ] Contract tests for both sources green in CI on the samples;
      `uv run pytest` green; the dependency policy test green on the new
      lock; no test reaches the network.
- [ ] Guard `Limits` per source recorded in the handoff and in
      `acquisition.json`; the terms sentences quoted in DATA-LICENSES.
- [ ] Data cards, DATA-LICENSES records, dictionary sections, sources.md
      rows, and the per-source snapshot-ID documentation all present.
- Evidence: CI green on Windows + Linux; the real run in the handoff with
  bytes, seconds, and digests; `git ls-files` shows no GTFS row and
  nothing under any `public/` zone.

## Tests / validation
`uv run pytest` (contracts on the samples; the download path's new
branches on crafted bytes: a PBF that must not be zip-inspected, an outer
zip whose inner zip fails a guard, an MD5 mismatch); the manual real run
above; `pre-commit run --all-files`; a scan of the diff for machine
identifiers, absolute paths, and any GTFS row.

## Resource budget
Network: about 370 MB once (346 MB extract, 21.6 MB feed, two terms
pages). Disk: the raw zone grows by about 370 MB, `intermediate/network/`
by the clipped PBF (tens of megabytes) and the two zips; well under the
50 GB workspace. RAM: pyosmium streams; the clip is minutes and well under
the routine 24 GB. Runtime: minutes. Session: one.

## Risks, rollback, stop condition
Geofabrik removes the dated file before the acquisition → **stop** and
surface: pick the newest dated extract with the owner and pin that
(ADR-0008 amended); never the `-latest` file. The MD5 or the SHA-256 of a
delivered file differs from the pinned value → the guarded path
quarantines it → **stop** (a provider-bytes finding). A terms sentence is
gone → quarantine, **stop**. The SEPTA release tag's asset is replaced (a
digest mismatch) → **stop**; pick a newer tag with the owner. pyosmium
fails to install from wheels on either platform → **stop**; the
alternative is feeding R5 the whole state extract (ADR-0008's recorded
fallback), decided with the owner. Rollback: snapshots are gitignored;
the code reverts cleanly; the `SNAPSHOT_IDS` change is one commit.

## Documentation / ADR updates
The documents listed under components; `roadmap/README.md` packet row;
`roadmap/architecture.md` stage row 8; `roadmap/sources.md`; CHANGELOG.
No new ADR (ADR-0008, written by EP-11, holds the pins).

## Handoff payload (filled 2026-09-03)
- **Packet:** EP-12 — work complete 2026-09-03, one session, at the S
  estimate; Planning Baseline v1.0. Work commit and CI run: see "Owner
  review" below (recorded once the owner has decided on the commit).
- **Files changed.** New: `phillysim/src/phillysim/adapters/osm.py`,
  `adapters/septa_gtfs.py`, `phillysim/src/phillysim/network.py`,
  `tests/contracts/test_osm_network.py`, `tests/contracts/test_septa_gtfs.py`,
  `tests/test_network.py`,
  `tests/fixtures/spine-samples/raw/osm_network/2026-09-03/` (the clipped
  PBF, 748,656 B, its MD5 sidecar, the terms excerpt, a Bucket B manifest)
  and `raw/gtfs/2026-09-03/` (a synthetic 2,552 B feed, the terms excerpt,
  a `synthetic: true` manifest), `docs/data-cards/osm-network.md`,
  `docs/data-cards/septa-gtfs.md`. Changed: `pipeline.py` (`SNAPSHOT_IDS`,
  `RAW_SNAPSHOTS` and `_raw` from the mapping, the `acquire` parameter
  `snapshot_ids`, digest pins as an injectable override, the `network`
  stage), `download.py` (`Fetch.digest` / `md5_of`, `check_digests`, the
  `digest` quarantine kind, the visible-text terms check, `digests_checked`
  in the acquisition record), `guards.py` (`inspect_nested_zip`),
  `contracts.py` (`ColumnSpec.maximum`), `adapters/__init__.py` (registry),
  `adapters/base.py` (`ANALYSIS_CRS` moved here, `WGS84`,
  `ROUTING_BUFFER_M`, `buffered_bounds`), `spine.py` (imports the CRS
  constant), `preflight.py` (`osmium` in the locked packages),
  `pyproject.toml` + `uv.lock` (`osmium>=4.3.1`), `tests/conftest.py`
  (per-source IDs in the sample transport, `sample_pins`, the sample
  bands), `tests/fixtures/spine-samples/{build_samples.py,README.md}`,
  `tests/integration/test_real_pipeline.py` (nine stages),
  `tests/{test_download,test_guards,test_basemap,test_destinations,
  test_slice_metric,test_spine_invariants}.py`,
  `tests/contracts/{test_harness,test_snap,test_spine_sources,
  test_tiger_roads}.py`, `docs/{DATA-LICENSES,data-dictionary}.md`,
  `docs/data-cards/{README,acs,cenpop,snap-retailers,tiger-roads,
  tiger-tracts}.md` (per-source IDs), `phillysim/README.md`,
  `roadmap/{architecture,sources,quality,README}.md`, `CHANGELOG.md`, this
  file.
- **Commands/tests run + results.** `uv run pytest` → **516 passed, 3
  skipped** in 38 s (461 before the packet; the three skips are the
  real-data-root tests); `pytest --real-data-root ../data` (spine,
  basemap, slice, destinations invariants on the real root) → 57 passed;
  `ruff check` / `ruff format --check` clean; `pre-commit run --all-files`
  all hooks passed (after the excerpt builder learned to strip trailing
  whitespace, so the committed sample survives the hook byte for byte);
  `uv lock --check` clean; the dependency policy test green on the new
  lock (`osmium` pulls `requests`, `urllib3`, `idna`, `certifi`,
  `charset-normalizer`; none is `GDAL` or `fiona`); the diff scanned for
  user names, machine identifiers, and absolute paths → none;
  `git ls-files` shows nothing under any `public/` zone or `site/dist/`
  and no GTFS row beyond the synthetic sample and the tinycity fixture.
  **Real run, working clone (`data/`):** `phillysim run --stage acquire`
  re-ran `acquire` (stale on the new `snapshot_ids` / `sources`
  parameters; 20.2 s): the five `2026-09-02` snapshots verified and
  re-used, the two new ones fetched (below). `run --stage network` re-ran
  `validate` (4.4 s, seven sources, no violation; the OSM read is
  header-only), `spine`, `snap_retailers`, and `basemap` (stale on
  `validation.json`; byte-identical outputs), and `network` (**181.7 s**;
  the report below). With the measured bands pinned, `phillysim run`
  re-ran `network` alone (**195.3 s**; `metrics` and `publish` fresh),
  then a second `run` → **0 ran, 9 skipped**; `status` → 9 fresh;
  `verify` → **7 of 7 snapshots, 9 of 9 stages**; `gate` green (5 files
  Bucket A / CC-BY-4.0, 4 sources, pipeline `real`). **The public zone is
  unchanged:** `basemap.geojson` `04141abb…0eafd`, `manifest.json`
  `7f2a19d4…c702`, `tracts.geojson` `18e6f19c…6191`, `sites.geojson`
  `65962e53…0403`, `tracts.csv` `ce380762…d5ce5`, `sites.csv`
  `ea3bdea9…f1a3`, every one equal to the EP-8b / EP-10 references; the
  four curated digests unchanged (`tracts_spine` `0c1d2349…fd3a2`,
  `snap_retailers` `a2887ec3…b63b`, `basemap_roads` `70469c4e…66ee`,
  `tract_metrics` `fa8b8bdd…4b9ce`).
- **The two acquisitions (one attempt each, through the guarded path).**
  `osm_network`: `https://download.geofabrik.de/north-america/us/pennsylvania-260831.osm.pbf`
  345,912,530 B in 15.5 s; the sidecar `…osm.pbf.md5` 62 B in 0.4 s; the
  region page `pennsylvania.html` 23,332 B in 0.5 s; 17.8 s in all. The
  delivered file's MD5 `a779d2ef14c8addce6eac207ab9cd851` equals the pin
  (ADR-0008) and the sidecar (`digests_checked` in `acquisition.json`
  records both); the terms phrases "created by OpenStreetMap
  Contributors" and "License: ODbL" found in the page's visible text;
  manifest `license_bucket = "B"` (the first real Bucket B manifest), the
  file never opened as an archive. `gtfs`:
  `https://github.com/septadev/GTFS/releases/download/v202609060/gtfs_public.zip`
  21,555,258 B in 0.8 s (redirected to
  `release-assets.githubusercontent.com`); SEPTA's developer page 17,557 B
  in 0.2 s; 1.0 s in all. SHA-256
  `4d3fa20ea094937a9bb6389ad52017e1ac90a564aee497f318797e1b1e4f07ab`
  equals GitHub's record; the outer zip inspected (2 members, ratio
  1.00); both "SEPTA reserves the right …" sentences found verbatim;
  manifest `license_bucket = "A"` with the terms and the
  facts-not-contents position in its note.
- **Guard `Limits` per source** (recorded in `acquisition.json`):
  `osm_network` 1 GiB file / 1 GiB extracted / ratio 50 / 50 members (the
  archive limits are declared, never exercised on a PBF); `gtfs` 128 MiB
  file / 1 GiB extracted / ratio 50 / 50 members, applied to the outer
  zip at acquisition and to each inner zip in place by the reader and
  again as a file by the unwrap (actual: outer 21.6 MB, inner 20.8 MB
  with 19 members and 0.76 MB with 20 members; the bus feed's
  `stop_times.txt` is 101.6 MB uncompressed).
- **The clipped network** (`intermediate/network/pennsylvania-260831-philadelphia-5km.osm.pbf`,
  box −75.360257 / 39.804412 / −74.880953 / 40.195375 WGS 84, the county
  bounds + 5 km in EPSG:26918): **5,803,119 nodes** (5,782,922 inside the
  box; the rest belong to ways crossing it), **921,869 ways** (224,252
  with a `highway` tag), **3,693 restriction relations**, **49,968,756 B**
  (sha256 `1f87cacb…3d3` on the pinned run, recorded for EP-13 to compare;
  both runs produced 49,968,756 B), from a state file of 45,125,372 nodes,
  4,903,283 ways, 55,814 relations; the clip's contract passed (header
  box equal to the clip box, counts inside the bands 4–8 M nodes /
  0.6–1.3 M ways now pinned in `adapters.osm`, every node inside the box
  or referenced by a kept way, highway ways present). **Stops outside the
  box:** bus/Metro 2,800 of 14,054 (8,080 inside the county's tracts);
  Regional Rail 39 of 156 (53 inside the tracts). Feed zips unwrapped:
  20,797,660 B and 757,262 B.
- **Resource observations:** one session, at the S estimate. Network:
  367.5 MB once (the two files, the sidecar, two terms pages), under a
  minute. Disk: the raw zone 469 MB (+367 MB), `intermediate/network/`
  69 MB, the data root about 540 MB; `.venv` 480 MB (+6 MB for `osmium`).
  Time: `network` about three minutes (three streaming passes over the
  state file in Python, then the ID-filtered write); every other stage
  seconds. RAM: not measured (EP-13's sampler); the clip holds about 5.8
  million node IDs and 0.9 million way IDs in Python sets. Suite: 516
  tests in 38 s (the sample clip adds about a second).
- **Decisions made (routine, agent's call, logged):** the routing sources
  are not tables, so their `read` (what `validate` checks) returns a
  **summary frame** (one row for the OSM header and MD5 checks, one row
  per GTFS feed) under a normal `SourceContract`, and the `network` stage
  calls the second read (`osm.clip`, `septa_gtfs.unwrap`); the OSM
  `validate` read opens the **header only** (the full scan is the clip's);
  the MD5 is **pinned in the adapter and the sidecar is fetched and
  compared too** (two provider-side checks; either mismatch is the
  `digest` stop); the GTFS SHA-256 is pinned the same way; **digest pins
  are injectable** (`real_pipeline(pins=…)`) so the suite pins the
  committed samples' digests without touching the adapters; the clip's
  **node and way bands are stage parameters** with the measured county
  values as defaults (the CI sample overrides them, so the CLI's `status`
  on a sample-built root reports `network` stale on parameters beside
  `spine`, asserted); the clip is implemented with **three pyosmium passes
  and an ID-filtered write** rather than `BackReferenceWriter`, to control
  the header (the box, the source's replication timestamp) and the order;
  the sample PBF is written **with the provider's header** (the state's
  bounding box, generator, timestamp) so it passes the same header
  contract as the real file; `ColumnSpec` gained `maximum`; `ANALYSIS_CRS`
  moved to `adapters.base` (the GTFS adapter needs it without importing
  `spine`); the sample excerpt builder strips trailing whitespace; the
  OSM CI sample is 749 KB (the six tracts are in Center City; under the
  5 MB hook and "a few hundred kilobytes" in spirit). **Owner-level
  decisions and deviations from the brief** are listed under "Owner
  review" below.
- **Unresolved risks / questions:** Geofabrik's retention of dated daily
  extracts is undocumented; the file is in the raw zone now, so a later
  fresh clone that cannot fetch `pennsylvania-260831.osm.pbf` is the
  refresh case (ADR-0008 amendment with the owner), not a break. The
  SEPTA agreement is revocable; the terms check runs at every
  acquisition. The rail feed's window ends 2026-10-17 (unchanged). Peak
  RSS of the clip is unmeasured until EP-13's sampler. Whether R5 builds
  the 50 MB clip within budget is what EP-13 measures; ADR-0008's
  whole-state fallback stands. For the third checkpoint: the CI samples
  README and DATA-LICENSES now name seven sources; the estimate-accuracy
  row for EP-12 (one session, S).
- **No-go areas touched:** none (no PHI, no secret, nothing deployed,
  nothing under a `public/` zone or `site/dist/` committed; the GTFS feed
  never left the data root: the raw zip and the two unwrapped zips live
  under `data/`, nothing from it under `public/` or `site/`; no GTFS row
  committed, the CI sample is synthetic; the OSM sample committed with the
  ODbL notice and "© OpenStreetMap contributors" in the samples README and
  its manifest; CI stays offline; no machine identifier or absolute path
  in a tracked file).
- `roadmap/README.md` packet row: updated with the work commit at the
  handoff commit (see below).
- **Exact next packet: EP-13** (`roadmap/EP-13-routing-toolchain-harness.md`:
  the pinned JDK 21 and R5 jar, r5py behind the wheel-only rule in the
  `routing` group, the RSS sampler, run records, the smoke route on this
  packet's `intermediate/network/`, the CI performance smoke).
