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

On Windows, clone with `git clone -c core.longpaths=true …` (or set
`git config --global core.longpaths true` first). Two file names under the
repository's vendored `source material/` tree exceed the default
260-character path limit once the clone sits in a directory path longer
than about 130 characters; the checkout fails otherwise (found at the EP-9
checkpoint's fresh-clone re-run).

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
    stages.py             stage registry: Stage / Pipeline declarations, cancel token (EP-4b)
    runner.py             fingerprints, state file, skip / resume / cancel, status, verify (EP-4b)
    preflight.py          disk / RAM / dependency / writable-root checks before a run (EP-4b)
    contracts.py          source-contract harness (schema/license/geometry) + the
                          locked analytic-table contract
    fixtures/tinycity.py  deterministic synthetic fixture generator (EP-3)
    fixtures/tinycity_contracts.py   contracts for the eight fake sources
    fixtures/pipeline.py  the eleven fixture stages behind `phillysim run --fixture` (EP-4b)
  tests/
    conftest.py           fixture-directory paths
    test_smoke.py         package import + CLI help/version/paths
    test_config.py        data-root resolution rules
    test_zones.py         snapshot-ID / source-name rules, layout creation, listing
    test_manifest.py      round-trip, field rules, snapshot + zone verification, `verify --raw`
    test_guards.py        one crafted malicious input per guard; admission + quarantine
    test_runner.py        registry rules, fingerprints, skip / resume / cancel, status, verify
    test_preflight.py     every check reported in one pass; simulated failures refuse the run
    test_dependency_policy.py   GDAL/fiona ban, with built-in negative checks
    test_tinycity_fixture.py    determinism + committed-golden checks
    contracts/            harness unit tests; tinycity sources positive/negative
    integration/          tinycity through all eleven stages via the CLI (M1 evidence)
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
unlisted file, or stray entry; `--raw DIR` checks any raw-zone directory on
its own. `verify` also checks the stage state (next section).

## Pipeline: stages, fingerprints, state, resume (EP-4b)

The pipeline is a fixed sequence of idempotent stages
(`phillysim.stages.Pipeline`), each a plain function that declares its inputs
and outputs as data-root-relative paths (`raw/<source>/<snapshot-id>`,
`curated/tracts_spine.parquet`, …) and a mapping of parameters. There is no
orchestrator. The runner (`phillysim.runner`) computes each stage's
**fingerprint** as the SHA-256 of its inputs' content digests plus its
parameters, nothing more, and records it in the state file
`<data root>/pipeline_state.json` ([shape](../docs/data-dictionary.md)).

- `phillysim run [--fixture] [--data-root DIR] [--stage NAME] [--param stage.key=value …]`
  runs preflight, then every stage in order, **skipping** any stage whose
  recorded fingerprint equals the current one and whose outputs are still on
  disk unaltered. A stage writes into `cache/staging/<stage>/` and the runner
  installs each output into its zone with an atomic rename only after the
  stage has finished, so a crash or cancellation never leaves a partially
  written file in a zone. `--stage NAME` stops after that stage; `--param`
  overrides a declared parameter (JSON value or string; unknown keys are
  refused) and, because parameters are part of the fingerprint, re-runs that
  stage and any downstream stage whose inputs then change in content.
- `phillysim status [--fixture]` prints each stage as **fresh** (fingerprint
  unchanged, outputs intact), **stale** (an input, a parameter, or an output
  changed), **missing** (never run, or an output is gone), or **incomplete**
  (the last attempt failed or was cancelled). Creates nothing.
- `phillysim verify [--fixture]` runs the EP-4a snapshot check on the raw zone
  and then checks the state file against the zones: every `done` stage's
  outputs present with their recorded digests, no stage left running,
  failed, or cancelled, no leftover staging, no unknown records. A failed
  stage is reported as *incomplete* by name; the next `run` resumes from it.
  Exit status 1 on any incomplete or broken stage. Creates nothing.

Cancellation is cooperative: the runner checks a `CancelToken` between
stages and a stage calls `ctx.checkpoint()` at its own safe points. A stage
cancelled mid-way is recorded as `cancelled`, its staging discarded, and its
previous outputs (if any) are no longer vouched for. Nothing in the state
file is machine-specific: relative paths, digests, parameters, UTC
timestamps; error text has the data root replaced by `<data-root>`.

**Preflight** (`phillysim.preflight`) runs before every `run` and reports all
checks in one pass: free disk under the data root, physical RAM, Python
version, the locked packages (geopandas, pyogrio, shapely, pyproj, duckdb,
pyarrow), and a writable root. A real run applies the architecture.md
budgets (≥150 GB free disk, 24 GB RAM); `--fixture` applies fixture-scale
thresholds (1 GiB each) and the report says so. Any failed check refuses
the run without touching the data root.

### The fixture pipeline

`phillysim run --fixture` runs the eleven-stage fixture pipeline
(`phillysim.fixtures.pipeline`) in its own data root, `<data root>/fixture/`
(gitignored): `acquire` generates tinycity and admits each of the eight raw
snapshots through `quarantine.admit`; `validate` checks every source against
its contract; `spine`, `demographics`, `destinations`, `conflate`, `network`,
`metrics`, and `publish` compute their outputs from the raw files; `hours`
and `travel_times` are explicit **stubs** that take their answers from the
generator's oracle until M4 (hours parsing) and M3 (routing) supply the real
logic. The four curated outputs equal the committed golden tables
(`tests/fixtures/tinycity/expected/`) by content, which the integration suite
asserts. CI runs `run`, `status`, and `verify --fixture` on Windows and Linux
(the M1 go/no-go). No real pipeline stages are registered yet: `run` and
`status` without `--fixture` say so and exit 1 until EP-5 adds the first
adapters.

## Resource baselines

Recorded at the EP-9 checkpoint (2026-09-02) from a fresh clone of `main`
at `a72d318` on the development machine (Windows 11), as the reference for
later checkpoints. Every number is trivially within the architecture.md
budgets at fixture scale.

| Measure | Baseline | Budget (architecture.md) |
|---|---|---|
| `git clone` | about 2 s | — |
| `uv sync --locked` | about 6 s with a warm uv cache; `.venv` 363 MB | — |
| `uv run pytest` (240 tests) | about 10 s | — |
| `phillysim run --fixture`, first run | 1.5 s wall including preflight; `acquire` and `validate` about 0.1 s each, every other stage under 0.05 s | routine peak RAM ≤24 GB (not measured yet) |
| second run (0 ran, 11 skipped) | about 1.0 s | — |
| `status --fixture`, `verify --fixture` | under 1 s each | — |
| fixture data root after a run | 148 KB (raw 55 KB, curated 44 KB, intermediate 29 KB, state file 12 KB, public 4 KB) | workspace ≤50 GB |
| preflight report | 429 GB free disk, 68.1 GB physical RAM, Python 3.13.15, all six locked packages present | real run needs ≥150 GB free and 24 GB RAM (would pass on this machine) |

Peak RSS is not measured yet: process-tree RSS sampling starts with the M3
spike harness, which is also where the CI performance-smoke test in
[roadmap/quality.md](../roadmap/quality.md) lands.

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
