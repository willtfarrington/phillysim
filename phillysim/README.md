# phillysim (package)

The Python package and uv project for phillysim. The repository root holds the
governance documents and roadmap; this directory holds the code. Read the
[repository README](../README.md) first for what the project is and is not.

## Setup (Windows-native is the primary path)

Requires [uv](https://docs.astral.sh/uv/). uv installs the pinned CPython
(`.python-version`, currently 3.13; the package declares `>=3.12`) on first
sync, so no system Python is needed or used.

```
cd phillysim
uv sync --locked
uv run phillysim --help
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run pre-commit install        # once per clone; hooks live in ../.pre-commit-config.yaml
```

Every runtime dependency installs from binary wheels on Windows (ADR-0001).
WSL2 is a documented fallback only; the CI matrix also runs the suite on Linux.

## Layout

```
phillysim/
  pyproject.toml          project metadata, locked stack, ruff/pytest config
  uv.lock                 committed lockfile (dependency version axis, ADR-0006)
  src/phillysim/
    cli.py                Typer entry point: `phillysim <command>`
    config.py             data-root resolution and zone paths
    zones.py              zone layout, source / snapshot-ID rules, snapshot listing (EP-4a)
    manifest.py           snapshot manifest model, canonical reader/writer, verify (EP-4a)
    guards.py             download guards: allowlist, size cap, zip-slip, bomb (EP-4a)
    quarantine.py         default-deny admission; failed snapshots move to quarantine/ (EP-4a)
    contracts.py          source-contract harness (schema/license/geometry) + the
                          locked analytic-table contract
    fixtures/tinycity.py  deterministic synthetic fixture generator (EP-3)
    fixtures/tinycity_contracts.py   contracts for the eight fake sources
  tests/
    conftest.py           fixture-directory paths
    test_smoke.py         package import + CLI help/version/paths
    test_config.py        data-root resolution rules
    test_zones.py         snapshot-ID / source-name rules, layout creation, listing
    test_manifest.py      round-trip, field rules, snapshot + zone verification, `verify` CLI
    test_guards.py        one crafted malicious input per guard; admission + quarantine
    test_dependency_policy.py   GDAL/fiona ban, with built-in negative checks
    test_tinycity_fixture.py    determinism + committed-golden checks
    contracts/            harness unit tests; tinycity sources positive/negative
    fixtures/tinycity/    golden fixture (README explains the layout)
    fixtures/tinycity-invalid/  injected-fault variant for negative tests
```

## The tinycity fixture

CI is offline by policy, so every pipeline stage is exercised on a synthetic
mini-geography instead of real data. `phillysim gen-tinycity --out DIR`
regenerates it deterministically; the committed copy under
`tests/fixtures/tinycity/` is checked against a fresh generation on every test
run. See [tests/fixtures/tinycity/README.md](tests/fixtures/tinycity/README.md)
for what it contains and [docs/data-dictionary.md](../docs/data-dictionary.md)
for the columns.

## Data root

The app owns one `data/` root with zones `raw`, `intermediate`, `curated`,
`public` (plus `quarantine` and `cache`). It resolves, in order, from the
`PHILLYSIM_DATA_ROOT` environment variable, then `<repo root>/data`, then
`<cwd>/data`. No absolute path is ever hard-coded; `phillysim paths` shows
the resolution without creating anything. Only `data/public/` may ever be
committed, and only via the publish gate ([docs/DATA-LICENSES.md](../docs/DATA-LICENSES.md)).

## Raw snapshots, manifests, and guards (EP-4a)

Every acquisition lands as an immutable snapshot directory
`data/raw/<source>/<snapshot-id>/` holding the acquired files, the archived
terms page, and a `manifest.json` in the shape documented in
[docs/data-dictionary.md](../docs/data-dictionary.md) (acquisition URL and
alternate URL, terms archive, license bucket, schema version, per-file
SHA-256). Snapshot IDs are the acquisition date, `YYYY-MM-DD`, with `-1`,
`-2`, … for a further acquisition the same day; existing snapshots are never
overwritten.

A staged snapshot enters the raw zone only through `phillysim.quarantine.admit`,
which is default-deny: the manifest must parse, the recorded URLs must be on
the adapter's domain allowlist (https only, no credentials, no IP literals),
every file must sit under the size cap, any zip must pass the zip-slip and
decompression-bomb checks, and every digest must match. On any failure the
whole directory moves to `data/quarantine/<source>/` with a reason file
beside it, and nothing there is ever read again. The guards
(`phillysim.guards`) work on local files and are tested only against crafted
inputs; no test or command in this package reaches the network.

`phillysim verify` checks every snapshot in the data root's raw zone against
its manifest and exits non-zero on the first tampered byte, missing or
unlisted file, or stray entry. `phillysim verify --fixture` runs the same
check on a freshly generated tinycity; `--raw DIR` checks any raw-zone
directory. EP-4b extends `verify` with stage-state coherence.

## Decisions this package honors

- [ADR-0001](../roadmap/adr/0001-language-and-stack.md): Python 3.12+/uv on
  native Windows; pyogrio-only geo I/O; `GDAL` and `fiona` PyPI packages banned
  and tested for.
- [ADR-0002](../roadmap/adr/0002-storage-geoparquet-duckdb.md): GeoParquet
  zone files + DuckDB spatial; no PostGIS.
- Locked-stack packages (geopandas, pyogrio, shapely, pyproj, duckdb, pyarrow)
  are declared now so the ban test and the Windows-wheel requirement are
  exercised from the first commit; r5py and the pinned JDK arrive with the M3
  routing spike.
