# EP-3 — tinycity synthetic fixture

**Status:** [x] 4ed065a · **Milestone:** M1 · **Effort:** M (1–2 sessions, high confidence) · **Parallel with:** —

## Outcome & value
A deterministic synthetic mini-geography ("tinycity": ~6 fake tracts, fake
POIs of all three destination categories with hours edge cases, tiny fake
network/GTFS stubs where cheap) with generator script and golden files,
sufficient to exercise every pipeline stage offline — plus the
source-contract test harness pattern (schema/license/geometry expectations)
proven against one fake source.

## Scope
- in: fixture generator, golden files, contract-harness pattern + one fake
  source contract, hours edge cases.
- out (explicit non-scope): real source adapters; routing (fixture provides
  precomputed fake travel times for downstream stages until M3).

## Prerequisites & locked decisions
- prerequisites: EP-2.
- locked decisions honored: the analytic schema contract {estimate, MOE, CV
  tier, reliability_action}; hours edge cases informed by methodology.md
  Tier 2 (weekend-only market, seasonal market, missing hours, malformed
  hours string).
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: fixture is wholly synthetic — no
derived real data; permissively licensed by construction (document that in
the fixture README).

## Likely components & contracts (proposed)
`tests/fixtures/tinycity/` + `tools/gen_tinycity.py`; `tests/contracts/`
harness; golden Parquet/GeoJSON files.

## Implementation notes
Determinism is the point: fixed seeds, stable ordering, identical checksums
on regeneration. Include at least one deliberately invalid variant for
negative testing.

## Acceptance criteria & evidence
- [x] Fixture generation deterministic (same checksums on two runs). —
  `test_two_generations_are_byte_identical` (both variants) compares every
  file's bytes and the `CHECKSUMS.txt` listing across two generations on
  every test run; `test_committed_fixture_matches_regeneration` holds the
  committed copy to the same standard (text byte-for-byte, Parquet by
  content).
- [x] Contract harness catches an injected schema violation (negative test).
  — `test_injected_schema_violation_on_the_fly` drops `store_type` from the
  golden retailers and requires exactly one schema violation naming it;
  `test_every_injected_fault_is_caught` requires all eight faults in the
  committed invalid variant to be caught by the check kind each targets;
  `tests/contracts/test_harness.py` exercises every check kind in isolation.
- Evidence: pytest suite green locally (76 tests) and in CI run
  [33658771646](https://github.com/willtfarrington/phillysim/actions/runs/33658771646)
  on `windows-latest` and `ubuntu-latest`;
  `phillysim/tests/fixtures/tinycity/README.md`.

## Tests / validation
pytest contract suite in CI.

## Resource budget
Trivial.

## Risks, rollback, stop condition
Fixture over-engineering — stop at "exercises every stage," not realism.

## Documentation / ADR updates
Fixture README; data dictionary seeded.

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-3 — done at commit `4ed065a` (+ this status commit).
  Planning Baseline v1.0. CI run
  [33658771646](https://github.com/willtfarrington/phillysim/actions/runs/33658771646)
  green on `windows-latest` and `ubuntu-latest`.
- **Files changed:** `phillysim/src/phillysim/contracts.py` (new: harness +
  locked analytic-table contract); `phillysim/src/phillysim/fixtures/`
  (`__init__.py`, `tinycity.py` generator, `tinycity_contracts.py`);
  `phillysim/src/phillysim/cli.py` (`gen-tinycity` command);
  `phillysim/tests/conftest.py`, `tests/test_tinycity_fixture.py`,
  `tests/contracts/{test_harness,test_tinycity_sources}.py`;
  `phillysim/tests/fixtures/.gitattributes`; generated golden files under
  `phillysim/tests/fixtures/tinycity/` (34 files + `CHECKSUMS.txt` + README)
  and `tinycity-invalid/` (30 files + `CHECKSUMS.txt` + README);
  `docs/data-dictionary.md` (new, schema version 1); `phillysim/README.md`,
  root `README.md`, `CHANGELOG.md`; this file.
- **Commands/tests run + results:** `uv run phillysim gen-tinycity --out …`
  for both variants (34 / 30 files); `uv run pytest` → 76 passed (24 before
  the packet); `uv run ruff check .` and `ruff format --check .` clean;
  `pre-commit run --all-files` with the new files staged → all hooks passed;
  `git ls-files --eol` confirms every fixture file is stored LF (text) or
  `-text` (Parquet) despite the machine's `core.autocrlf=true`; scan of the
  staged tree for usernames / absolute paths → none. Fixture directories are
  119 KB and 65 KB.
- **Resource observations:** trivial, as budgeted; single session. Generation
  and the full suite run in seconds.
- **Decisions made (revisable, below ADR level):**
  - The generator lives in the package (`phillysim.fixtures.tinycity`) behind
    a CLI command rather than the brief's proposed `tools/gen_tinycity.py`,
    so EP-4's `phillysim run --fixture` can import it and the tests never
    shell out. The brief labeled its components "proposed".
  - Golden Parquet files are compared by *content* against a fresh
    generation, text files byte-for-byte; both are also listed in
    `CHECKSUMS.txt`. Rationale: Parquet bytes change with the pinned pyarrow /
    geopandas writer versions, and a Dependabot bump should not break CI for
    a golden that is semantically unchanged.
  - Geography placed in the open Atlantic with FIPS 99/999 so the fixture can
    never be mistaken for, or pass a filter meant for, Philadelphia County.
    Coordinates stay EPSG:4326; the analysis CRS is EP-5's decision.
  - Contracts declared for all eight fake sources, not just one (cheap, and
    EP-4 needs them for the fixture pipeline); the "one fake source" proof
    the brief asks for is the retailers contract.
  - Travel-time stand-in: Manhattan distance at 4.8 km/h + 1 min access,
    85th percentile = 1.15 × median (walk) / 1.25 × (transit), stub transit
    line along the bottom tract row with walk+transit = min(walk, 0.6 × walk
    + 5 min). Documented in `fixture.json`; replaced by M3.
  - Fixture assumptions that M5 must confirm or revise: CV computed as
    (MOE / 1.645) / estimate with tiers at 12 % / 40 %;
    `reliability_action = interval-only` exactly when the tier is 3; `moe`
    and `cv_tier` null for quantities without sampling error. Recorded in
    the data dictionary as assumptions.
  - Pinned analysis weeks interpreted as the first full Monday-to-Sunday
    week (2026-06-01 and 2026-02-02 for the fixture year).
  - Hours in the raw meal-site layer are contract-valid strings; whether
    "25:00" parses is the parser's call (M4), so the contract does not
    pattern-check them. Markets' free-text hours likewise.
  - `.gitattributes` scoped to `phillysim/tests/fixtures/` (`* -text`,
    `*.parquet binary`) rather than repo-wide.
- **Owner decisions taken interactively (2026-09-02):** commit and push
  (yes — work at `4ed065a`, this status commit follows); keep the generator
  in the package behind `phillysim gen-tinycity` rather than a
  `tools/gen_tinycity.py` script (yes); keep contracts for all eight fake
  sources rather than trimming to one (yes); accept the golden-file policy
  of content comparison for Parquet and byte comparison for text (yes).
- **Unresolved risks/questions:** the Parquet golden files are written by
  the pinned pyarrow 25.0.1 / geopandas 1.1.4; if a future writer changes
  the *content* representation (not just bytes), the golden test will say so
  and the fixture is regenerated. The 120-minute censoring branch, POI
  de-duplication, and ACS ratio-MOE propagation are deliberately not
  exercised (fixture README lists them); each lands with its own packet.
  Owner triage carried over: seven open Dependabot security alerts and four
  Dependabot PRs (#1–#4) all target the vendored `source material/` JKAN
  tree (Ruby/JS), which policy says is never modified — the owner should
  either close them and exclude that directory from Dependabot, or accept
  the alerts as reference-material noise. Not touched in this packet.
  Resolved 2026-09-02 after the packet closed: config entries added  
  (`cd6de7e`), PRs closed, alerts dismissed.
- **No-go areas touched:** none — no real data acquired or derived, no
  network calls, `source material/` untouched, no machine identifiers or
  absolute paths in tracked files (scanned), fixture wholly synthetic and
  documented as such with its MIT-by-construction license.
- **Exact next packet:** EP-4 (manifest engine, zones, stages, preflight,
  guards — proven on tinycity).
