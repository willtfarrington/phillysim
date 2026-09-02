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
| Source contracts | schema/license/geometry expectations per adapter, on offline fixtures | CI | yes for the eight tinycity sources (`tests/contracts/`, EP-3); real adapters add theirs from EP-5a |
| Golden math | metric formulas, MOE propagation, bin edges vs hand-computed answers | CI | partly: the CV-tier rule is pinned (`test_cv_tier_rule`); MOE propagation and bin edges arrive with M5 |
| Geospatial invariants | CRS, geometry validity, county bounds, join cardinality, GEOID integrity | CI | not yet (EP-5b) |
| Integration | tinycity synthetic fixture through all 11 stages | CI | yes (`tests/integration/`, plus the `run` / `status` / `verify --fixture` CI steps, EP-4b) |
| UI E2E | Playwright: map/table sync, panel focus flow, deep links, exports | CI | not yet (M6) |
| Accessibility (automated) | axe-core on built site | CI | not yet (M6) |
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
