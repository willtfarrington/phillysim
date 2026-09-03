# Quality: versioning, testing, reproducibility, release gates

## Version axes (ADR-0006) `required roadmap decision`

| Axis | Recorded where | Bumps when |
|---|---|---|
| Code/app (SemVer, 0.x pre-v1) | git tags / pyproject | code changes |
| Dependencies | uv lockfile (manifest-referenced) | lock update |
| Dataset snapshots | per-source date-stamped snapshot IDs in checksummed manifests | controlled refresh |
| Schema | integer field in manifests + data dictionary | breaking table-shape change (with migration note) |
| Methods/parameters | version field in the metric registry (manifest-recorded) | any metric definition or pinned-parameter change — never silent |
| Public release | git release tag | pins ALL of the above |

Reproducing an old result: check out the release tag → restore pinned
snapshots via manifests (or use the published derived tables if upstream is
gone) → run documented commands → checksum-identical within the pinned
Windows environment; canonicalized-value hashes cross-platform.
`required release evidence`

## Test matrix

| Layer | Contents | Runs | Exists at EP-9 (2026-09-02) |
|---|---|---|---|
| Source contracts | schema/license/geometry expectations per adapter, on offline fixtures | CI | yes for the eight tinycity sources (`tests/contracts/`, EP-3) and, since EP-5a, for the three real spine sources on committed real-shaped samples (`tests/contracts/test_spine_sources.py`); the download path itself is tested on crafted local bytes and the suite disables sockets |
| Golden math | metric formulas, MOE propagation, bin edges vs hand-computed answers | CI | partly: the CV-tier rule is pinned (`test_cv_tier_rule`); since EP-7 the build-time bin edges and classes (`tests/test_publish.py`) and the QA slice metric against hand-computed distances and a brute-force check on the samples (`tests/test_slice_metric.py`); MOE propagation arrives with M5 |
| Publish gate | per-file license labels derived from the sources' buckets, in-file labels and notices, WGS 84 within bounds, CSV escaping, no path leakage, prohibited vocabulary, QA-only flags, format parity | CI | yes since EP-7 (`tests/test_publish.py`: green on the fixture's zone, one negative per check, the intentionally mislabeled file first; the `publish` stage refuses to install a zone the gate rejects; `phillysim gate --fixture` is a CI step) |
| Geospatial invariants | CRS, geometry validity, county bounds, join cardinality, GEOID integrity | CI | yes since EP-5b (`tests/test_spine_invariants.py` on the committed samples; the same module runs on the real spine with `pytest --real-data-root DIR`, recorded in the packet handoff; the `spine` and `demographics` stages enforce the same checks in-stage); the SNAP retailer layer has its own set since EP-6 (`tests/test_destinations.py`; enforced in-stage) |
| Golden mapping | the store-type → format-class table pinned row by row, its rules (format-based vocabulary, strict on unknown labels), and the method card it renders into | CI | yes since EP-6 (`tests/test_store_format.py`; a change is a methods-version bump) |
| Integration | tinycity synthetic fixture through all 11 stages | CI | yes (`tests/integration/`, plus the `run` / `status` / `verify` / `gate --fixture` CI steps, EP-4b and EP-7); the real pipeline's seven stages run offline on the committed samples through a fake transport (EP-5a–EP-7) |
| UI E2E | Playwright: map/table sync, panel focus flow, deep links, exports | CI | seed since EP-8a (`tests/test_site_browser.py`: the fixture-built slice page renders map + tables offline, keyboard order, 320 px reflow, reduced motion, no-WebGL fallback; the machine's own Chrome or Edge, no browser download); panel, deep links, exports at M6 |
| Accessibility (automated) | axe-core on built site | CI | yes since EP-8a (zero violations asserted in the same module, Windows and Linux) |
| Site build | the page built only from a gated public zone, verbatim copies, deterministic bytes, vendored library digests, no off-origin loads | CI | yes since EP-8a (`tests/test_sitebuild.py`; the `site build --fixture` CI step) |
| Performance smoke | stage runtimes/memory vs budgets on fixture | CI | not yet; baselines recorded in `phillysim/README.md` (EP-9); the CI test lands with the M3 spike |
| Manual release checklist | below | per release | M7 |

CI: GitHub Actions, fully offline (fixtures only), SHA-pinned actions,
minimal token permissions. Live-API acquisition happens only in the
controlled refresh workflow, never CI.

## Release checklist (manual gate) `required release evidence`

1. Keyboard-only + NVDA pass on the built site (documented).
2. Pre-publication harm/claims review (governance.md) incl. claims-matrix
   compliance sweep.
3. License/attribution audit: bucket labels on every `data/public/` file AND
   site data payloads; export notices; basemap/OSM attribution.
4. Delisting-policy presence + channel check.
5. Privacy-note presence; no analytics/third-party calls (verified in build).
6. Reproducibility rehearsal: fresh clone → commands → checksums match.
7. Changelog + version-axis pins recorded in the release notes.
