# EP-5b — Curated tract spine + geospatial invariants + analysis-CRS ADR

**Status:** [x] b61d060 (done 2026-09-02) · **Milestone:** M2 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-5 (2026-09-02, EP-9 pre-read; EP-5a is the other half)

## Outcome & value
The curated geography spine on real data: one GeoParquet table keyed by
2020 GEOID for Philadelphia County's roughly 408 tracts, with decennial
population, population-weighted centroids, and geometry in a single pinned
projected analysis CRS chosen and recorded in an ADR here; ACS estimates
and margins of error joined to that spine; and the geospatial invariant
tests (CRS, geometry validity, county bounds, 2020-vintage GEOID integrity,
join cardinality) that every later packet inherits. This half carries the
EP-5 set's milestone-level evidence: `phillysim run --stage spine` from a
fresh clone reproduces the checksummed curated spine.

## Scope
- in:
  1. Analysis CRS chosen (a single projected CRS for Philadelphia; WGS 84
     only at the publication boundary, methodology.md) and recorded as
     ADR-0007; the data dictionary records it and says which tables carry
     it.
  2. Real `spine` and `demographics` stages registered in the real
     pipeline after EP-5a's `acquire` / `validate`: county filter applied
     (if EP-5a stored state-level files), GEOIDs validated as 2020-vintage
     Philadelphia County tracts, centroids joined one-to-one, ACS columns
     (methodology.md's variable list) joined with their MOE, suppressed
     cells left null (ADR-0004).
  3. Invariant test module: CRS as declared, all geometries valid, every
     geometry within the county bounds, GEOID pattern and count, exactly
     one centroid and one ACS row per tract; runs in CI on EP-5a's samples
     and manually on the real spine.
  4. Data cards (spine sources) as EP-5 required: what TIGER, CenPop, and
     ACS contribute, vintages, terms, and the CRS.
- out (explicit non-scope): destination sources (EP-6); metrics and the
  public zone (EP-7); the block-group centroid sensitivity (M5).

## Prerequisites & locked decisions
- prerequisites: EP-5a.
- locked decisions honored: 2020 tracts, Philadelphia County only; the
  analysis CRS is chosen and ADR'd **in this packet**; ADR-0004 (no
  suppression, nulls stay null); `docs/data-dictionary.md` curated spine
  shape (schema version bump only if the shape changes, with a migration
  note); ADR-0006 axes.
- dependencies: none beyond EP-5a's snapshots.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: nothing under a tracked
`public/` zone; the curated spine stays in the gitignored curated zone;
data-card wording inside the claims matrix (docs/CLAIMS.md).

## Likely components & contracts (proposed)
`src/phillysim/spine.py` (or the stage functions in the real pipeline
module); `tests/test_spine_invariants.py`; `roadmap/adr/0007-analysis-crs.md`;
`docs/data-dictionary.md` (CRS recorded; spine and ACS tables confirmed);
`docs/` data cards for the three spine sources.

## Implementation notes
Reuse the fixture pipeline's stage names and output paths
(`curated/tracts_spine.parquet`, `intermediate/acs_tracts.parquet`) so the
architecture.md stage table and the fixture integration suite describe both
pipelines. Population-weighted centroids come from CenPop, never computed
from geometry. Record the spine's content digest in the handoff as the
reproducibility reference.

## Acceptance criteria & evidence
- [x] `phillysim run --stage spine` from a fresh clone (after EP-5a's
      acquisition) reproduces the curated spine with the digest recorded in
      the handoff; `phillysim verify` passes. (Fresh clone of `b61d060`:
      identical digests to the working clone; handoff below.)
- [x] Invariant tests green in CI (samples) and on the real spine
      (manual, recorded); ACS MOE columns present. (CI run 33699313284;
      `pytest --real-data-root` on both clones, below.)
- [x] ADR-0007 exists and the data dictionary records the analysis CRS.
- Evidence: CI run green on Windows + Linux; the real run and the spine
  digest in the handoff.

## Tests / validation
`uv run pytest` (invariants on samples; fixture integration suite still
green); manual real run with the invariant module against the real spine.

## Resource budget
Trivial (a few MB of curated data; seconds).

## Risks, rollback, stop condition
Tract count or GEOID vintage mismatch against the pinned vintages →
**stop** and surface (a source changed under the manifest). CRS choice
affects every later distance-bearing computation: choose it once, in the
ADR, with the alternatives recorded. Rollback: curated zone is gitignored;
code reverts cleanly.

## Documentation / ADR updates
ADR-0007 (analysis CRS); data dictionary; data cards; `phillysim/README.md`;
CHANGELOG; packet row in `roadmap/README.md` (and the EP-5 set is then
complete).

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-5b — done at commit `b61d060` (+ this status commit); the
  EP-5 set is complete. Planning Baseline v1.0. CI run
  [33699313284](https://github.com/willtfarrington/phillysim/actions/runs/33699313284)
  on `b61d060` green on `windows-latest` and `ubuntu-latest` (pytest, ruff,
  the three fixture-pipeline steps; CI never runs the real pipeline and
  never passes `--real-data-root`).
- **Files changed:** new `phillysim/src/phillysim/spine.py`,
  `tests/test_spine_invariants.py`, `roadmap/adr/0007-analysis-crs.md`,
  `docs/data-cards/{README,tiger-tracts,cenpop,acs}.md`; `pipeline.py`
  (`spine` + `demographics` registered after `validate`; docstring);
  `tests/conftest.py` (`--real-data-root` option and fixture);
  `tests/integration/test_real_pipeline.py` (four stages, spine assertions,
  six-tract parameter override); `docs/data-dictionary.md` (status, CRS
  table, spine section, `acs_tracts` row, raw-source intro);
  `phillysim/README.md` (layout, real-pipeline section, manual invariant
  run); `roadmap/architecture.md` (stage rows 3–4); `roadmap/quality.md`
  (geospatial-invariants row); `roadmap/methodology.md` (CRS line);
  `CHANGELOG.md`; `roadmap/README.md` (packet row); this file.
- **Commands/tests run + results.** Working clone: `uv run pytest` → all
  passed, 2 skipped (the two real-spine tests, which need
  `--real-data-root`); `ruff check` / `ruff format --check` clean;
  `pre-commit run --all-files` all hooks passed; staged diff scanned for
  usernames / absolute paths → none. **Real run, working clone (`data/`):**
  `phillysim run` skipped `acquire` / `validate` (fresh from EP-5a), ran
  `spine` 0.3 s and `demographics` 0.9 s; second run 0 ran / 4 skipped;
  `status` 4 fresh; `verify` 3 of 3 snapshots, 4 of 4 stages done and
  intact. `pytest tests/test_spine_invariants.py --real-data-root ../data
  -s` → 19 passed: 408 tracts, 2020 population 1,603,797 (the Bureau's
  county total), no ACS null in any of the four columns, 403 of 408
  population-weighted centers inside their own tract. **Fresh-clone
  rehearsal of `b61d060`** (scratch directory, `git clone -c
  core.longpaths=true`, deleted afterwards): `uv sync --locked`; `uv run
  pytest` all passed (2 skipped); `phillysim run --stage spine` fetched
  everything again (ACS 18,313,708 + 65,043,091 bytes, CenPop 144,662,
  TIGER 13,109,450, terms page 311,057 × 3; every fetch one attempt;
  `acquire` 4.6 s, `validate` 1.1 s, `spine` 0.2 s); `run` then ran
  `demographics` 0.9 s; third `run` 0 ran / 4 skipped; `status` 4 fresh;
  `verify` 4 of 4 stages done and intact; the invariant module passed on
  that spine too; `git status` clean; data root 94 MB.
  **Reproducibility reference:** `curated/tracts_spine.parquet`
  sha256 `0c1d2349ad52da8919a3372bfcaf08528ef98b370c48d2e4ec2909f3964fd3a2`
  (470,192 bytes) and `intermediate/acs_tracts.parquet` sha256
  `94cefd3aa13fcb6999fcab0833261251871a098ecc50448143da3cbfdd14742e`
  (13,105 bytes), **byte-identical between the working clone and the fresh
  clone** (same lockfile, same provider bytes, deterministic GeoParquet
  writer).
- **Resource observations:** curated spine 470 KB, ACS join 13 KB; each
  stage under a second; one session (S estimate held). Network only for
  the rehearsal's re-acquisition (97 MB). Spine sanity: total tract area
  368.6 km² in EPSG:26918 (the county is about 370 km²); geometric versus
  population-weighted centroid distance median 63 m, maximum 1,858 m.
- **Decisions made (owner-reviewed 2026-09-02, all recommended options
  accepted):**
  - **ADR-0007, analysis CRS = EPSG:26918** (NAD 83 / UTM zone 18N, metres)
    over EPSG:32129 (PA South, metres) and EPSG:2272 (PA South, US survey
    feet, the City's CRS); alternatives and the publication-boundary datum
    note are in the ADR. Recorded in `phillysim.spine.ANALYSIS_CRS`, the
    `spine` stage's `crs` parameter (fingerprinted), the GeoParquet
    metadata, methodology.md, and the data dictionary's CRS table.
  - **Spine shape unchanged, schema version stays 1:** geometry in the
    analysis CRS; `centroid_lon` / `centroid_lat` remain the degrees CenPop
    publishes (the routing-origin form); `phillysim.spine.centroids_in`
    projects them on demand. Projected centroid columns were offered and
    declined (they would have forced generator and golden changes for a
    fixture city outside zone 18).
  - **Commit, push, fresh-clone rehearsal, handoff:** done as above.
  - Routine (agent's call, logged): the `spine` and `demographics` stages
    enforce the invariants on their own output (a real run cannot produce a
    spine that fails them), with `expected_tracts` a stage parameter so the
    six-tract CI samples run the same code under `--param` (and the CLI's
    `status` then rightly reports that spine as stale on parameters, which
    the integration test asserts); the real-spine tests are gated by a
    pytest option rather than an environment variable so the manual run is
    one visible command; `spine` declares `validation.json` as an input so
    a contract change re-runs it; the tinycity fixture pipeline keeps its
    own geographic CRS (the dictionary's CRS table says so and why); data
    cards live one file per source under `docs/data-cards/` with an index,
    ready for the M6 site.
- **Unresolved risks / questions:** none blocking. Notes for EP-6: join
  destinations to the spine with the projected geometry (EPSG:26918), and
  keep any source's own coordinates as delivered in its raw table; five
  tracts have zero 2020 population and five population-weighted centers
  lie outside their own tract (all named in the CenPop data card), which
  the metrics stage (M5) must decide how to display; the ACS 2020–2024
  total-population estimate differs from the 2020 count tract by tract, as
  the ACS card says.
- **No-go areas touched:** none (no PHI, no secret, nothing under a tracked
  `public/` zone, curated zone gitignored, CI offline).
- `roadmap/README.md` packet row updated to `[x] b61d060`; the M2 heading
  stays open (EP-6, EP-7, EP-8 remain).
- **Exact next packet: EP-6** (SNAP retailer adapter + supermarket-format
  classification; M-sized, so read at pickup and split before work starts
  if it will not fit one session).
