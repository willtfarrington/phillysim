# EP-6 — SNAP retailer adapter + supermarket-format classification

**Status:** [x] 907f8f8 (done 2026-09-02; pickup pre-read: fit one session, not split) · **Milestone:** M2 · **Effort:** M (1–2 sessions, medium confidence) · **Parallel with:** —

## Outcome & value
SNAP retailer acquisition (manifest-recorded), Philadelphia filter, a
store-type → format-class mapping table (published in the method card;
**format-based names only**), a point GeoParquet layer keyed by stable site
ID, and the all-SNAP-retailer variant retained for M5's SRAM validation. The
OSM supermarket cross-check is deferred to M4 conflation (noted, not
implemented).

## Scope
- in: adapter, filter, classification mapping + method-card stub, point
  layer, sanity counts.
- out (explicit non-scope): conflation/dedup across sources (M4); hours (the
  SNAP file has none).

## Prerequisites & locked decisions
- prerequisites: EP-5.
- locked decisions honored: AM-4 (SNAP-derived supermarket-format points);
  the claims-vocabulary ban (no nutrition-quality adjectives on
  project-derived categories — including in code identifiers).
- dependencies: USDA SNAP retailer file (dual-URL manifest field — FNS→FNA
  domain migration in progress).

## Safety preconditions
Standing policy (see EP-1). Packet-specific: classification wording reviewed
against docs/CLAIMS.md before merge.

## Likely components & contracts (proposed)
`src/phillysim/adapters/snap.py`;
`src/phillysim/classify/store_format.py` + mapping table in config;
`tests/contracts/test_snap.py`.

## Implementation notes
Store-type mapping is a published, versioned artifact (methods axis): keep it
in config, render it into the method-card stub.

## Acceptance criteria & evidence
- [x] Classified point layer reproducible from fresh clone (working clone
  and fresh-clone digests in the handoff).
- [x] Mapping table renders into the method-card stub
  (`docs/method-cards/store-formats.md`; `tests/test_store_format.py` keeps
  it in sync).
- [x] Philadelphia counts sanity-checked against the source's own totals
  (recorded in handoff and in the SNAP data card).
- Evidence: contract tests + golden mapping test green.

## Tests / validation
Contract tests on fixture; golden mapping test.

## Resource budget
Trivial.

## Risks, rollback, stop condition
Store-type field semantics differ from documentation → stop, record evidence,
adjust the mapping with a methods-version note.

## Documentation / ADR updates
Method-card stub (destination layers); data card (SNAP).

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-6 — done at commit `907f8f8` (+ this status commit).
  Planning Baseline v1.0. Pickup pre-read judged the M-sized packet to fit
  one session (the download path, contract harness, runner, spine, and
  sample machinery all existed), so it was not split; it did fit. CI run
  [33701811742](https://github.com/willtfarrington/phillysim/actions/runs/33701811742)
  on `907f8f8` green on `windows-latest` and `ubuntu-latest` (pytest, ruff,
  the three fixture-pipeline steps; CI never runs the real pipeline).
- **Files changed:** new `phillysim/src/phillysim/adapters/snap.py`,
  `classify/{__init__.py,store_format.py,store_formats.csv}`,
  `destinations.py`; `tests/contracts/test_snap.py`,
  `tests/test_store_format.py`, `tests/test_destinations.py`,
  `tests/fixtures/spine-samples/raw/snap_retailers/2026-09-02/` (3 files);
  `docs/method-cards/store-formats.md` (first method card),
  `docs/data-cards/snap-retailers.md`; changed `adapters/__init__.py`
  (registry), `pipeline.py` (`snap_retailers` source and stage; `acquire`
  params gain `snapshot_id` + `sources`), `runner.py` (declared-outputs
  staleness; install retry 6 → 10 attempts), `cli.py` (status column
  width), `tests/contracts/test_spine_sources.py`,
  `tests/integration/test_real_pipeline.py` (five stages),
  `tests/test_runner.py`, `tests/fixtures/spine-samples/{README.md,
  build_samples.py}` (SNAP sample; dBASE header date pinned),
  `docs/data-cards/README.md`, `docs/DATA-LICENSES.md` (USDA record),
  `docs/data-dictionary.md` (CRS row, SNAP layer section, raw-source
  section, intermediate row), `roadmap/{architecture,quality,sources,
  milestones}.md` (stage 4b; golden-mapping row; source row; M4 + M5
  carry-ins), `phillysim/README.md`, `CHANGELOG.md`, `roadmap/README.md`
  (packet row), this file.
- **Commands/tests run + results.** Working clone: `uv run pytest` → all
  passed, 2 skipped (real-spine tests); `ruff check` / `ruff format
  --check` clean; `pre-commit run --all-files` all hooks passed; staged
  diff scanned for usernames / absolute paths → none. **Real run, working
  clone (`data/`):** first `run --stage snap_retailers` re-ran `acquire`
  (parameters changed: the new source) and fetched the SNAP zip
  (24,036,753 bytes, 1.1 s, one attempt, delivered by the FNA URL through
  its content-delivery redirect) and the provider's data page (44,082
  bytes); the install of the staged snapshot then failed on Windows with
  `PermissionError` after the runner's six retries (Defender holding the
  fresh 24 MB zip), the retry was raised to ten attempts (about 14 s), and
  the second run acquired again (1.3 s) and completed: `validate` 3.3 s
  (SNAP: 1,609 rows, no violation; nulls only in Additional Address,
  Street Number, Zip4, End Date), `spine` re-ran on the changed
  `validation.json` and reproduced the spine byte-for-byte
  (`0c1d2349…fd3a2`), `demographics` skipped, `snap_retailers` 2.4 s; a
  third `run` 0 ran / 5 skipped; `status` 5 fresh; `verify` 4 of 4
  snapshots, 5 of 5 stages done and intact; `pytest
  tests/test_spine_invariants.py --real-data-root ../data` 19 passed.
  **Fresh-clone rehearsal of `907f8f8`** (scratch directory, `git clone -c
  core.longpaths=true` from GitHub, deleted afterwards): `uv sync
  --locked`; `uv run pytest` all passed (2 skipped); `phillysim run
  --stage snap_retailers` acquired all four sources (acquire 11.1 s incl.
  121 MB), then validate 3.0 s, spine 0.2 s, demographics 0.8 s,
  snap_retailers 2.3 s (18.4 s wall in all); second `run` 0 ran / 5
  skipped; `status` 5 fresh; `verify` 5 of 5; `git status` clean; data
  root 117 MB. **Reproducibility reference:**
  `curated/snap_retailers.parquet` sha256
  `a2887ec3e0a70c30f1812efa88de353c605adbd65cd3c12f9cf699a3a852b63b`
  (138,406 bytes), **byte-identical between the working clone and the
  fresh clone**; spine and `acs_tracts` digests unchanged from EP-5b.
- **Sanity check against the source's own totals (acceptance
  criterion).** The pinned file has 703,441 authorization spells
  nationwide; 249,063 open at 2025-12-31 (9,818 in Pennsylvania, 1,609 in
  Philadelphia County). USDA's FY 2021 Retailer Management Year End
  Summary (the last with a static state table; FY 2024/2025 are
  dashboards) reports 254,350 authorized firms nationally and 10,110 in
  Pennsylvania at 2021-09-30; reconstructing that date from the file's
  authorization / end dates gives 246,165 and 9,939 (3.2 % and 1.7 %
  lower); FY 2017: 263,105 reported vs 254,861 reconstructed (3.1 %
  lower). The gap matches the two USDA store types the historical file
  never carries (`Direct Marketing Farmer`, `Internet Retailer`). No
  Philadelphia figure is published by USDA; the county's 1,609 is
  consistent with the state ratio. Store-type semantics matched the USDA
  definitions page (labels abbreviated, codes crosswalked; `Wholesaler`
  and `Unknown` occur in the file but not on the page) → not the stop
  condition; recorded in the method card. Layer counts: 164
  supermarket-format (95 Supermarket + 69 Super Store), 340 tracts with
  any open retailer, 115 with a supermarket-format one, 2 points outside
  every tract, 13 coordinate-sharing pairs.
- **Resource observations:** one session (the M estimate's low end held
  for the fourth M packet in a row); SNAP zip 24 MB (95 MB CSV read in
  place, about 2 s per read), layer 138 KB, data root 117 MB; every stage
  under 4 s; network 121 MB for a fresh clone.
- **Decisions made (owner-reviewed 2026-09-02, all recommended options
  accepted):**
  - **Supermarket-format = USDA `Supermarket` + `Super Store`**
    (mapping `store-formats-1`; seven format classes; `Large Grocery
    Store` in `grocery`, its inclusion recorded as an M5 sensitivity
    carry-in in milestones.md).
  - **Archived page for USDA = the provider's data page in force**
    (`source-page.html`), checked for the official-site banner and the
    as-of sentence, because usda.gov's Policies and Links page answers
    HTTP 403 to non-browser clients and the FNA site carries no license
    statement; license basis 17 U.S.C. § 105; evidence in DATA-LICENSES.
  - **Two rows outside every tract kept with null `geoid`** (all-retailer
    count matches the provider; M4 carry-in decides drop / re-geocode).
  - **Commit, push, fresh-clone rehearsal, handoff:** done as above.
  - Routine (agent's call, logged): the classified layer is a real-only
    stage named `snap_retailers` writing `curated/snap_retailers.parquet`
    (per-source destination layers sit upstream of the shared
    `destinations` stage, which M4 builds over them; the fixture pipeline
    is untouched), one layer serving both the supermarket-format subset
    and the all-retailer variant via `supermarket_format`; the adapter's
    read keeps only open authorization spells so the key is the record ID
    (history stays in the stored file); the contract's allowed store-type
    set is the mapping's vocabulary, making a new provider label a
    contract violation (the packet's stop condition) rather than a silent
    `other`; the mapping is a packaged CSV rendered into the method card
    with a sync test and `python -m phillysim.classify.store_format`; the
    allowlist names the FNA content-delivery host the download redirects
    to; coordinates declared WGS 84 (datum unstated by the provider);
    `acquire` takes the source list and snapshot ID as parameters and the
    runner marks a stage stale when its declared outputs differ from the
    recorded ones (the first run after registering a source had skipped
    `acquire` as fresh); the sample builder pins the dBASE header's write
    date (the TIGER sample was not byte-reproducible across days).
- **Unresolved risks / questions:** the historical file's URL carries a
  year range (`…data2005-2025.zip`) and USDA refreshes it about yearly, so
  the pinned snapshot may stop being acquirable from a fresh clone after
  the next refresh (the scoped reproducibility claim: derived tables
  remain; the as-of phrase check stops acquisition rather than delivering
  a different file); the content-delivery host name in the allowlist is
  provider infrastructure and may change (a redirect to a new host fails
  the allowlist loudly). Notes for EP-7: read the supermarket-format
  points from `curated/snap_retailers.parquet` where `supermarket_format`
  is true; geometry is already EPSG:26918; two rows have null `geoid`.
- **No-go areas touched:** none (no PHI, no secret, nothing under a
  tracked `public/` zone, curated zone gitignored, CI offline; store names
  are provider text and are not published by this packet).
- `roadmap/README.md` packet row updated to `[x] 907f8f8`; the M2 heading
  stays open (EP-7, EP-8 remain).
- **Exact next packet: EP-7** (thin-slice metric + public zone + license
  bucketing; M-sized, so read at pickup and split before work starts if
  it will not fit one session).
