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
    contracts.py          source-contract harness (schema/license/geometry) + the
                          locked analytic-table contract
    fixtures/tinycity.py  deterministic synthetic fixture generator (EP-3)
    fixtures/tinycity_contracts.py   contracts for the eight fake sources
  tests/
    conftest.py           fixture-directory paths
    test_smoke.py         package import + CLI help/version/paths
    test_config.py        data-root resolution rules
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
