# EP-5b — Curated tract spine + geospatial invariants + analysis-CRS ADR

**Status:** [ ] planned · **Milestone:** M2 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-5 (2026-09-02, EP-9 pre-read; EP-5a is the other half)

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
- [ ] `phillysim run --stage spine` from a fresh clone (after EP-5a's
      acquisition) reproduces the curated spine with the digest recorded in
      the handoff; `phillysim verify` passes.
- [ ] Invariant tests green in CI (samples) and on the real spine
      (manual, recorded); ACS MOE columns present.
- [ ] ADR-0007 exists and the data dictionary records the analysis CRS.
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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results (spine digest; CI run ID)
- resource observations
- decisions/ADRs made (ADR-0007); unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated to `[x] <commit>`
- exact next packet: EP-6
