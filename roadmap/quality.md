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

| Layer | Contents | Runs |
|---|---|---|
| Source contracts | schema/license/geometry expectations per adapter, on offline fixtures | CI |
| Golden math | metric formulas, MOE propagation, bin edges vs hand-computed answers | CI |
| Geospatial invariants | CRS, geometry validity, county bounds, join cardinality, GEOID integrity | CI |
| Integration | tinycity synthetic fixture through all 11 stages | CI |
| UI E2E | Playwright: map/table sync, panel focus flow, deep links, exports | CI |
| Accessibility (automated) | axe-core on built site | CI |
| Performance smoke | stage runtimes/memory vs budgets on fixture | CI |
| Manual release checklist | below | per release |

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
