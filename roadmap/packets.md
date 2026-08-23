# Near-horizon work packets (issue-ready)

Packets EP-01–EP-08 cover M0–M2 to the full template standard
([_TEMPLATE.md](_TEMPLATE.md)). M3+ packets are authored at each milestone's
refinement gate — not speculatively. File paths and command names below are
**proposed contracts** until first implemented. Standing safety policy
(applies to every packet): no source datasets committed; no machine
identifiers or absolute local paths in tracked files; license buckets
respected; no outbound calls beyond the documented allowlist.

---

## EP-01 — Repository governance bootstrap (M0) — S (1, high)

**Outcome:** the public repo is honest and governed at every commit:
reframed README ("measuring access, not modeling outcomes"; "sim" definition;
AI disclosure; non-endorsement), GitHub repo description updated to match,
comprehensive .gitignore (data/ zones, secrets/.env, caches, logs, notebook
outputs, local DBs), DATA-LICENSES stub with the City-license caveat and
license-bucket rules, CLAIMS.md instantiated from the charter's claims rows,
CONTRIBUTING + SECURITY + correction/delisting policy stubs.
**Scope out:** any Python code; CI (EP-02).
**Prereqs:** none — first packet. Locked: charter.md claims rows, AM-1/AM-4
vocabulary, governance.md delisting policy.
**Safety preconditions:** claims wording matches charter exactly; no
affiliation implications; vendored `source material/` untouched.
**Components (proposed):** README.md rewrite; .gitignore; docs/CLAIMS.md;
docs/DATA-LICENSES.md; CONTRIBUTING.md; SECURITY.md; docs/policies.md.
**Acceptance:** every file passes a read-through against charter.md +
governance.md; repo description updated (GitHub settings, owner action noted
in handoff); `git status` clean.
**Tests:** manual review checklist in packet; markdown lint if trivial.
**Budget:** trivial.
**Risks/stop:** wording drifts from claims matrix → stop, reconcile charter
first.
**Docs:** this packet IS docs; changelog started.
**Handoff:** per template.

---

## EP-02 — Python scaffold + offline CI skeleton (M0) — M (1–2, high)

**Outcome:** `uv`-managed package `phillysim` under `phillysim/` with pinned
Python 3.12+, Typer CLI entry (`phillysim --help` works), config module
(app-owned `data/` root; no absolute paths), pre-commit (format/lint), and a
GitHub Actions workflow: SHA-pinned actions, minimal permissions, offline,
running lint + a placeholder test; secret scanning + push protection + Dependabot
enabled (owner clicks documented in handoff).
**Scope out:** any pipeline logic; fixtures.
**Prereqs:** EP-01. Locked: ADR-0001 (stack; GDAL/fiona PyPI ban enforced via
a dependency-check test), B3-07 CLI shape.
**Safety preconditions:** lockfile committed; no network in CI.
**Components (proposed):** `phillysim/pyproject.toml`, `phillysim/src/phillysim/{__init__,cli,config}.py`,
`.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `tests/test_smoke.py`,
`tests/test_dependency_policy.py` (asserts banned packages absent).
**Acceptance:** fresh clone → documented setup commands → CLI help + tests
green locally and in CI.
**Tests:** `uv run pytest`; CI run green.
**Budget:** trivial.
**Risks/stop:** Windows wheel failure for any pinned dep → stop, record, and
resolve versions before proceeding (do not swap stack unilaterally).
**Docs:** README setup section; ADR-0001 committed.

---

## EP-03 — tinycity synthetic fixture (M1) — M (1–2, high)

**Outcome:** a deterministic synthetic mini-geography ("tinycity": ~6 fake
tracts, fake POIs of all three categories with hours edge cases, tiny fake
network/GTFS stubs where cheap) with generator script and golden files,
sufficient to exercise every pipeline stage offline, plus the source-contract
test harness pattern (schema/license/geometry expectations) proven against
one fake source.
**Scope out:** real source adapters; routing (fixture provides precomputed
fake travel times for downstream stages until M3).
**Prereqs:** EP-02. Locked: WS5→WS4 schema contract {estimate, MOE, CV tier,
reliability_action}; hours edge cases informed by methodology.md Tier 2.
**Safety preconditions:** fixture is wholly synthetic — no derived real data;
permissive by construction.
**Components (proposed):** `tests/fixtures/tinycity/` + `tools/gen_tinycity.py`,
`tests/contracts/` harness, golden parquet/GeoJSON files.
**Acceptance:** fixture generation is deterministic (same checksums twice);
contract harness catches an injected schema violation (negative test).
**Tests:** pytest contract suite in CI.
**Budget:** trivial.
**Risks/stop:** fixture over-engineering — stop at "exercises every stage,"
not realism.
**Docs:** fixture README; data dictionary seeded.

---

## EP-04 — Manifest/snapshot engine + zones + stage runner (M1) — L (2, medium; split allowed at engine/runner boundary)

**Outcome:** the pipeline backbone: snapshot IDs, checksummed manifests
(acquisition URL + dual-URL field, terms-archive pointer, schema version,
license bucket), raw→intermediate→curated→public zone layout under `data/`,
idempotent stage runner with input fingerprints (unchanged inputs → skip),
resume/cancel semantics, preflight checks (disk/RAM/deps), quarantine path
for validation failures, and download guards (size caps, zip-slip,
decompression-bomb, domain allowlist) — all proven on tinycity.
**Scope out:** real adapters; drift detection beyond schema-hash comparison.
**Prereqs:** EP-03. Locked: architecture.md zones/stages; ADR-0006 axes
fields.
**Safety preconditions:** quarantine-on-failure is default-deny; `data/`
gitignored; manifests contain no machine identifiers.
**Components (proposed):** `src/phillysim/{manifest,zones,stages,preflight,guards}.py`,
CLI verbs `phillysim run/status/verify --fixture`.
**Acceptance:** full fixture pipeline runs; re-run skips unchanged stages;
kill mid-stage → `verify` reports coherent state; injected oversized/zip-slip
fixture is quarantined (negative tests).
**Tests:** integration suite on tinycity in CI; guard negative tests.
**Budget:** trivial at fixture scale.
**Risks/stop:** fingerprint design churn → keep to content-hash of inputs +
params; anything fancier is out of scope.
**Docs:** ADR-0006 committed; pipeline README section; data dictionary.

---

## EP-05 — Geography spine adapters: TIGER + CenPop + ACS (M2) — M (1–2, high)

**Outcome:** real acquisition scripts (manifest-recorded, checksummed,
bbox-filtered at ingest) for TIGER/Line 2025 Philadelphia tracts, CenPop2020
population-weighted centroids, ACS 5-yr 2020–2024 selected tables with MOE;
curated GeoParquet spine keyed by GEOID; geospatial invariant tests (CRS,
validity, county bounds, 2020-vintage GEOID integrity, join cardinality).
**Scope out:** destination sources; metrics.
**Prereqs:** EP-04. Locked: 2020 tracts; pinned vintages; pinned analysis CRS
(chosen and ADR'd in this packet).
**Safety preconditions:** Census terms honored; snapshots stay in gitignored
raw zone; only fixture-scale samples may become CI fixtures if permissively
redistributable (they are; document it).
**Components (proposed):** `src/phillysim/adapters/{tiger,cenpop,acs}.py`;
`tests/contracts/test_spine.py`.
**Acceptance:** `phillysim run --stage spine` from fresh clone reproduces
checksummed curated spine; invariants green; MOE columns present.
**Tests:** contract + invariant suites (fixtures in CI; real run documented
manually in handoff).
**Budget:** network few hundred MB; disk <2 GB; minutes runtime.
**Risks/stop:** ACS table selection creep → only variables named by
methodology.md; more requires a methods-version bump.
**Docs:** data cards (spine sources); ADR-000x CRS.

---

## EP-06 — SNAP retailer adapter + supermarket-format classification (M2) — M (1–2, medium)

**Outcome:** SNAP retailer acquisition (manifest-recorded), Philadelphia
filter, store-type → format-class mapping table (published in the method
card; **format-based names only**), point GeoParquet keyed by stable site ID,
plus the all-SNAP-retailer variant retained for M5 SRAM validation; OSM
supermarket cross-check deferred to M4 conflation (noted, not implemented).
**Scope out:** conflation/dedup across sources; hours (SNAP file has none).
**Prereqs:** EP-05. Locked: AM-4; claims vocabulary ban.
**Safety preconditions:** classification wording reviewed against CLAIMS.md
before merge; no nutrition adjectives anywhere including code identifiers.
**Components (proposed):** `src/phillysim/adapters/snap.py`;
`src/phillysim/classify/store_format.py` + mapping table in config;
`tests/contracts/test_snap.py`.
**Acceptance:** classified point layer reproducible; mapping table renders
into a method-card stub; counts sanity-checked against the source's own
Philadelphia totals (recorded in handoff).
**Tests:** contract tests on fixture; golden mapping test.
**Budget:** trivial.
**Risks/stop:** store-type field semantics differ from documentation → stop,
record evidence, adjust mapping with method-version note.
**Docs:** method-card stub (destination layers); data card (SNAP).

---

## EP-07 — Thin-slice metric + public zone + license bucketing (M2) — M (1–2, medium)

**Outcome:** the deliberately trivial slice metric (straight-line QA distance
tract-centroid → nearest supermarket-format point — labeled QA-only, never a
published access measure), flowing through curated → public zone with
license-bucket labeling (this table is Bucket A until OSM enters at M3+),
build-time bin computation, and the publish-gate check (license labels,
bounds, no raw-path leakage) — proving the public boundary machinery.
**Scope out:** real travel times; site UI beyond EP-08's minimal page.
**Prereqs:** EP-06. Locked: AM-1 bucket rules; schema contract.
**Safety preconditions:** public zone contains only tract-level aggregates +
facility points already public upstream; publish gate green before anything
leaves curated.
**Components (proposed):** `src/phillysim/metrics/slice.py`,
`src/phillysim/publish/{bucket,gate}.py`; `data/public/` outputs.
**Acceptance:** publish gate blocks an intentionally mislabeled file
(negative test); public GeoJSON/CSV validate against schema + bucket rules.
**Tests:** golden metric test; gate negative test; integration on fixture.
**Budget:** trivial.
**Risks/stop:** temptation to publish the QA metric as an access measure —
prohibited; it exists to prove plumbing.
**Docs:** data dictionary (public schema v1).

---

## EP-08 — Minimal slice page (M2) — M (1–2, medium)

**Outcome:** a minimal static page (no framework decision creep: MapLibre +
vanilla JS/TS as ADR'd) rendering the public slice GeoJSON over the
public-domain minimal basemap (first cut: county boundary + major roads from
TIGER, meeting contrast spec), with an HTML table of the same data, vintage
line, and attribution block — served by local dev server; deployed to Pages
only if the owner opts to show work-in-progress (default: not deployed).
**Scope out:** the full Explore UI, panel, deep links, exports (M6).
**Prereqs:** EP-07. Locked: ADR-0005 basemap; WS5 palette/contrast; table
parity principle (even the slice page has the table).
**Safety preconditions:** no third-party calls; attribution present; page
labeled work-in-progress, no claims.
**Components (proposed):** `site/` (index.html, main.js, styles);
`src/phillysim/publish/sitebuild.py`; Playwright smoke + axe check.
**Acceptance:** page renders map + table from public zone artifacts offline;
axe: no violations; keyboard reaches all controls.
**Tests:** Playwright + axe in CI against fixture-built site.
**Budget:** trivial.
**Risks/stop:** UI scope creep → anything beyond "render + table + vintage +
attribution" belongs to M6.
**Docs:** site README section; screenshot into repo (own work, no license
issue).

---

## Checkpoint packet (recurring, ~every 5 packets) — S

Integration re-run on fixtures + real spine; docs/data-dictionary sync;
license-label sweep; performance vs budgets; estimate-accuracy review;
re-plan if triggers hit (milestones.md).
