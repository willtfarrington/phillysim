"""Command-line entry point (``phillysim``).

Plain Typer commands over idempotent, fingerprint-checked stage functions; no
orchestrator (architecture.md, B3-07). Inspection commands (``version``,
``paths``), the fixture generator (``gen-tinycity``), and the pipeline verbs
from the stage runner (EP-4b): ``run`` brings a pipeline up to date (skipping
fresh stages), ``status`` reports every stage as fresh / stale / missing /
incomplete, ``verify`` checks the raw zone against its manifests (EP-4a)
and the stage state against the zones, and ``gate`` (EP-7) re-runs the publish
gate on the installed public zone (license labels, bounds, escaping, no path
leakage; CI runs it on the fixture). ``site build`` / ``site serve`` (EP-8a)
build the static slice page from a gated public zone and serve it locally.
``toolchain install`` / ``toolchain check`` (EP-13) install and verify the pinned
JDK and R5 jar project-local; ``route smoke`` runs the first JVM route in a
sampled child process and leaves run records under ``<data root>/runs/routing/``.

Without ``--fixture`` the verbs use the real pipeline (:mod:`phillysim.pipeline`,
EP-5a onward) on the resolved data root, and ``run`` acquires real snapshots
over the network through the guarded download path. ``--fixture`` selects the
tinycity fixture pipeline and its own data root, ``<data root>/fixture/``;
``--data-root DIR`` points any verb at an explicit root. Only ``run`` ever
creates directories.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer

from phillysim import __version__, runner
from phillysim.config import ENV_DATA_ROOT, Settings
from phillysim.fixtures.pipeline import FIXTURE_ROOT_NAME, fixture_pipeline
from phillysim.fixtures.tinycity import Variant, write_fixture
from phillysim.manifest import verify_raw_zone
from phillysim.pipeline import real_pipeline
from phillysim.preflight import FIXTURE_SCALE, REAL_RUN, run_preflight
from phillysim.publish import sitebuild
from phillysim.publish.export import PUBLIC_MANIFEST, PUBLIC_ZONE
from phillysim.publish.gate import check_public_zone
from phillysim.routing import smoke, toolchain
from phillysim.runner import StateError, verify_state
from phillysim.stages import CancelledError, Pipeline, PipelineError, StageError, parse_params

app = typer.Typer(
    name="phillysim",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
)

FixtureOption = Annotated[
    bool,
    typer.Option("--fixture", help="Use the tinycity fixture pipeline and its own data root."),
]
DataRootOption = Annotated[
    Path | None,
    typer.Option("--data-root", help="Use this data root instead of the resolved one."),
]


@app.callback()
def main() -> None:
    """phillysim - measures access to health-relevant community resources in Philadelphia.

    Descriptive access measurement at the 2020 census-tract level. No simulation,
    prediction, clinical decision support, scores, or rankings.
    """


@app.command()
def version() -> None:
    """Print the installed package version."""
    typer.echo(__version__)


@app.command()
def paths(
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    """Show the resolved data root and its zones. Creates nothing."""
    settings = Settings.load()
    if as_json:
        payload = {
            "data_root": str(settings.data_root),
            "data_root_source": settings.data_root_source,
            "zones": {name: str(path) for name, path in settings.zones().items()},
        }
        typer.echo(json.dumps(payload, indent=2))
        return
    typer.echo(f"data root: {settings.data_root}")
    typer.echo(f"  resolved from: {settings.data_root_source}")
    typer.echo(f"  override with: {ENV_DATA_ROOT}=<path>")
    for name, path in settings.zones().items():
        typer.echo(f"  {name:<13}{path}")


@app.command("gen-tinycity")
def gen_tinycity(
    out: Annotated[Path, typer.Option("--out", help="Directory to write the fixture into.")],
    variant: Annotated[
        Variant, typer.Option("--variant", help="'valid' (golden) or 'invalid' (injected faults).")
    ] = Variant.VALID,
) -> None:
    """Regenerate the tinycity synthetic fixture (deterministic; see tests/fixtures/tinycity/)."""
    digests = write_fixture(out, variant)
    typer.echo(f"wrote {len(digests)} files ({variant.value}) under {out}")


# --- pipeline verbs --------------------------------------------------------------------------


def _resolve_root(fixture: bool, data_root: Path | None) -> tuple[Path, str]:
    """The data root a verb operates on, and a label for messages."""
    if data_root is not None:
        return data_root.expanduser().resolve(), str(data_root)
    base = Settings.load().data_root
    if fixture:
        return base / FIXTURE_ROOT_NAME, "fixture data root"
    return base, "data root"


def _pipeline(fixture: bool) -> Pipeline:
    """The pipeline for this root: the fixture's, or the real one (EP-5a onward)."""
    return fixture_pipeline() if fixture else real_pipeline()


@contextmanager
def _download_log() -> Iterator[None]:
    """Show the download path's progress lines (URL, bytes, retries) while a real run runs."""
    log = logging.getLogger("phillysim.download")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("     %(message)s"))
    log.addHandler(handler)
    previous = log.level
    log.setLevel(logging.INFO)
    try:
        yield
    finally:
        log.removeHandler(handler)
        log.setLevel(previous)


@app.command()
def run(
    fixture: FixtureOption = False,
    data_root: DataRootOption = None,
    stage: Annotated[
        str | None,
        typer.Option("--stage", help="Run through this stage only (its predecessors first)."),
    ] = None,
    param: Annotated[
        list[str] | None,
        typer.Option(
            "--param",
            help="Override a stage parameter: stage.key=value (JSON or string); repeatable.",
        ),
    ] = None,
) -> None:
    """Run the pipeline: preflight, then every stage whose inputs or parameters changed.

    Fresh stages are skipped; a failed or cancelled stage is recorded and re-run next time.
    Exit status 1 if preflight refuses or a stage fails.
    """
    pipeline = _pipeline(fixture)
    try:
        pipeline = pipeline.with_params(parse_params(param or []))
        if stage is not None:
            pipeline.through(stage)
    except PipelineError as exc:
        raise typer.BadParameter(str(exc)) from exc
    root, label = _resolve_root(fixture, data_root)
    typer.echo(f"pipeline {pipeline.name!r} at {label}: {root}")
    preflight = run_preflight(root, FIXTURE_SCALE if fixture else REAL_RUN)
    for line in preflight.lines():
        typer.echo(line)
    if not preflight.ok:
        typer.echo("refusing to run: preflight failed")
        raise typer.Exit(code=1)
    try:
        with _download_log():
            report = runner.run(root, pipeline, through=stage, echo=typer.echo)
    except (StageError, StateError) as exc:
        typer.echo(f"FAIL {exc}")
        typer.echo(
            "the stage is recorded as incomplete; `phillysim verify` names it and the next "
            "`phillysim run` resumes from it"
        )
        raise typer.Exit(code=1) from exc
    except CancelledError as exc:
        typer.echo(
            "cancelled; the stage is recorded as incomplete and the next run resumes from it"
        )
        raise typer.Exit(code=130) from exc
    typer.echo(f"{len(report.ran)} stage(s) ran, {len(report.skipped)} skipped (fresh)")


@app.command()
def status(
    fixture: FixtureOption = False,
    data_root: DataRootOption = None,
) -> None:
    """Report every stage as fresh, stale, missing, or incomplete. Creates nothing."""
    pipeline = _pipeline(fixture)
    root, label = _resolve_root(fixture, data_root)
    typer.echo(f"pipeline {pipeline.name!r} at {label}: {root}")
    if not root.is_dir():
        typer.echo("data root does not exist: every stage is missing (run `phillysim run` first)")
        raise typer.Exit(code=1)
    try:
        rows = runner.status(root, pipeline)
    except StateError as exc:
        typer.echo(f"FAIL {exc}")
        raise typer.Exit(code=1) from exc
    for row in rows:
        typer.echo(f"{row.status:<11}{row.name:<16}{row.detail}")
    counts = {
        kind: sum(1 for r in rows if r.status == kind)
        for kind in ("fresh", "stale", "missing", "incomplete")
    }
    typer.echo(", ".join(f"{n} {kind}" for kind, n in counts.items()))


@app.command()
def verify(
    fixture: FixtureOption = False,
    raw: Annotated[
        Path | None,
        typer.Option("--raw", help="Verify this raw-zone directory only (snapshot level)."),
    ] = None,
    data_root: DataRootOption = None,
) -> None:
    """Verify raw snapshots against their manifests and the stage state against the zones.

    Exit status 1 if any snapshot fails, the raw zone holds a stray entry, a recorded stage's
    outputs are missing or altered, or any stage is incomplete. Creates nothing.
    """
    if fixture and raw is not None:
        raise typer.BadParameter("--fixture and --raw are mutually exclusive")
    if raw is not None:
        if not raw.is_dir():
            typer.echo(f"raw zone not found: {raw}: nothing to verify")
            raise typer.Exit(code=1)
        report = verify_raw_zone(raw)
        typer.echo(f"verifying raw zone: {raw}")
        for line in report.lines():
            typer.echo(line)
        raise typer.Exit(code=0 if report.ok else 1)

    root, label = _resolve_root(fixture, data_root)
    pipeline = _pipeline(fixture)
    raw_zone = root / "raw"
    if not raw_zone.is_dir():
        hint = " (run `phillysim run --fixture` first)" if fixture else ""
        typer.echo(f"raw zone not found for {label}: nothing to verify{hint}")
        raise typer.Exit(code=1)
    typer.echo(f"verifying raw zone: {label}: {raw_zone}")
    zone_report = verify_raw_zone(raw_zone)
    for line in zone_report.lines():
        typer.echo(line)
    typer.echo(f"verifying stage state: pipeline {pipeline.name!r}")
    state_report = verify_state(root, pipeline)
    for line in state_report.lines():
        typer.echo(line)
    if not (zone_report.ok and state_report.ok):
        raise typer.Exit(code=1)


@app.command()
def gate(
    fixture: FixtureOption = False,
    data_root: DataRootOption = None,
    public: Annotated[
        Path | None,
        typer.Option(
            "--public",
            help="Gate this public-zone directory on its own (bounds from its manifest only).",
        ),
    ] = None,
) -> None:
    """Run the publish gate on the installed public zone (ADR-0003): every file listed and
    labeled with the bucket its sources require, in-file labels, WGS 84 within bounds, CSV
    escaped, no zone or absolute path leaked, no prohibited vocabulary, formats in parity.

    Exit status 1 on any violation or when there is no public zone to check. Creates nothing.
    """
    if fixture and public is not None:
        raise typer.BadParameter("--fixture and --public are mutually exclusive")
    if public is not None:
        target, bounds, label = public.expanduser().resolve(), None, str(public)
    else:
        root, label = _resolve_root(fixture, data_root)
        target = root / PUBLIC_ZONE
        params = _pipeline(fixture)["publish"].params
        bounds = tuple(float(b) for b in params["bounds"])
        label = f"{label}: {target}"
    typer.echo(f"publish gate: {label}")
    if not target.is_dir() or not any(target.iterdir()):
        typer.echo("no public zone to check (run the pipeline through `publish` first)")
        raise typer.Exit(code=1)
    problems = check_public_zone(target, bounds=bounds)
    for problem in problems:
        typer.echo(f"FAIL {problem}")
    if problems:
        typer.echo(f"publish gate: {len(problems)} violation(s); nothing here may be published")
        raise typer.Exit(code=1)
    manifest = json.loads((target / PUBLIC_MANIFEST).read_text("utf-8"))
    for name, entry in sorted(manifest["files"].items()):
        typer.echo(
            f"ok   {name:<16} Bucket {entry['bucket']} ({entry['license']['spdx_id']}), "
            f"{entry['rows']} row(s)"
        )
    typer.echo(
        f"publish gate: green ({len(manifest['files'])} file(s) labeled, "
        f"{len(manifest['sources'])} source(s), pipeline {manifest['pipeline']!r}, "
        f"methods {manifest['methods_version']!r})"
    )


# --- the slice page (EP-8a) ----------------------------------------------------------------------

site_app = typer.Typer(
    name="site",
    help="Build and serve the static slice page from a gated public zone (EP-8a).",
    no_args_is_help=True,
    rich_markup_mode=None,
)
app.add_typer(site_app, name="site")

OutOption = Annotated[
    Path | None,
    typer.Option("--out", help="Write the site here (default: <repo>/site/dist, gitignored)."),
]


def _site_dist(out: Path | None) -> Path:
    if out is not None:
        return out.expanduser().resolve()
    return sitebuild.site_source_dir() / sitebuild.DIST_DIR_NAME


@site_app.command("build")
def site_build(
    fixture: FixtureOption = False,
    data_root: DataRootOption = None,
    public: Annotated[
        Path | None,
        typer.Option("--public", help="Build from this public-zone directory (gated on its own)."),
    ] = None,
    out: OutOption = None,
) -> None:
    """Build the static slice page: re-run the publish gate on the public zone, copy its files
    (the basemap among them) verbatim, lay the page and the vendored MapLibre beside them.
    Replaces a previous build at the output directory; refuses anything else there.

    Exit status 1 if the zone fails the gate or there is no zone to build from.
    """
    if fixture and public is not None:
        raise typer.BadParameter("--fixture and --public are mutually exclusive")
    if public is not None:
        zone, bounds, label = public.expanduser().resolve(), None, str(public)
    else:
        root, label = _resolve_root(fixture, data_root)
        zone = root / PUBLIC_ZONE
        params = _pipeline(fixture)["publish"].params
        bounds = tuple(float(b) for b in params["bounds"])
        label = f"{label}: {zone}"
    dist = _site_dist(out)
    typer.echo(f"site build: {label}")
    if not zone.is_dir() or not any(zone.iterdir()):
        typer.echo("no public zone to build from (run the pipeline through `publish` first)")
        raise typer.Exit(code=1)
    try:
        report = sitebuild.build_site(zone, dist, bounds=bounds)
    except sitebuild.SiteBuildError as exc:
        typer.echo(f"FAIL {exc}")
        raise typer.Exit(code=1) from exc
    for name, digest in sorted(report["public_files"].items()):
        typer.echo(f"ok   data/{name:<16} {digest[:12]}")
    layers = ", ".join(f"{layer} ({n})" for layer, n in report["basemap"]["layers"].items())
    typer.echo(f"basemap: data/{report['basemap']['file']} holds {layers}")
    typer.echo(
        f"site build: done at {dist} (pipeline {report['pipeline']!r}, "
        f"MapLibre GL JS {report['vendor']['maplibre-gl']['version']}, work in progress)"
    )
    typer.echo("serve it with `phillysim site serve`; nothing here is deployed")


@site_app.command("serve")
def site_serve(
    out: OutOption = None,
    port: Annotated[int, typer.Option("--port", help="TCP port (0 = pick a free one).")] = 8000,
    host: Annotated[
        str, typer.Option("--host", help="Interface to bind; loopback by default.")
    ] = "127.0.0.1",
) -> None:
    """Serve a built site over plain HTTP on loopback (the local dev server). Ctrl-C stops it."""
    dist = _site_dist(out)
    try:
        server = sitebuild.serve(dist, port=port, host=host, log=typer.echo)
    except sitebuild.SiteBuildError as exc:
        typer.echo(f"FAIL {exc}")
        raise typer.Exit(code=1) from exc
    except OSError as exc:
        typer.echo(f"FAIL cannot bind {host}:{port}: {exc}")
        raise typer.Exit(code=1) from exc
    bound_host, bound_port = server.server_address[:2]
    typer.echo(f"serving {dist} at http://{bound_host}:{bound_port}/ (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        typer.echo("stopped")
    finally:
        server.server_close()


# --- the routing toolchain and harness (EP-13) -------------------------------------------------

toolchain_app = typer.Typer(
    name="toolchain",
    help="Install and check the pinned routing toolchain, project-local (EP-13, ADR-0008).",
    no_args_is_help=True,
    rich_markup_mode=None,
)
app.add_typer(toolchain_app, name="toolchain")

HomeOption = Annotated[
    Path | None,
    typer.Option(
        "--home",
        help="Install under this project directory instead of <repo>/phillysim (tests).",
    ),
]


def _toolchain(home: Path | None) -> toolchain.Toolchain:
    if home is not None:
        return toolchain.Toolchain(home.expanduser().resolve())
    return toolchain.Toolchain.default()


@toolchain_app.command("install")
def toolchain_install(home: HomeOption = None) -> None:
    """Download the pinned Temurin JDK 21 build and the pinned R5 jar through the guarded
    path, verify both against ADR-0008's digests, and install them under <repo>/phillysim/
    (.jdk/ and .r5/, gitignored; nothing on PATH). Idempotent.

    Exit status 1 on a digest mismatch (the download is deleted), a guard refusal, or a
    JDK that does not report the pinned version.
    """
    chain = _toolchain(home)
    typer.echo(f"toolchain home: {chain.home} ({chain.platform})")
    try:
        with _download_log():
            toolchain.install(chain, echo=typer.echo)
    except toolchain.ToolchainError as exc:
        typer.echo(f"FAIL {exc}")
        raise typer.Exit(code=1) from exc
    for line in toolchain.check(chain).lines():
        typer.echo(line)


@toolchain_app.command("check")
def toolchain_check(home: HomeOption = None) -> None:
    """Report the installed toolchain: the JDK's `java -version`, the jar's digest against
    the pin, the record, and the routing group's package versions. Exit status 1 unless
    every check passes. Creates nothing.
    """
    chain = _toolchain(home)
    typer.echo(f"toolchain home: {chain.home} ({chain.platform})")
    report = toolchain.check(chain)
    for line in report.lines():
        typer.echo(line)
    if not report.ok:
        raise typer.Exit(code=1)


route_app = typer.Typer(
    name="route",
    help="Routing runs in a sampled child process (EP-13); records under <data root>/runs/.",
    no_args_is_help=True,
    rich_markup_mode=None,
)
app.add_typer(route_app, name="route")


@route_app.command("smoke")
def route_smoke(
    data_root: DataRootOption = None,
    home: HomeOption = None,
    repeats: Annotated[
        int, typer.Option("--repeats", min=1, help="How many runs in a row (default 3).")
    ] = smoke.REPEATS,
    single_departure: Annotated[
        bool,
        typer.Option(
            "--single-departure",
            help="A one-minute departure window instead of 60 (EP-15's hand check).",
        ),
    ] = False,
    departure: Annotated[
        str,
        typer.Option("--departure", help="Local departure time HH:MM on the pinned Wednesday."),
    ] = smoke.DEPARTURE_TIME,
) -> None:
    """The smoke route: one tract center to one supermarket-format retailer on the clipped
    network, walk and walk+transit, run three times; each run leaves a record. Exit status
    1 if preflight (the real-run thresholds plus the toolchain check) refuses or any run
    does not complete.
    """
    root, label = _resolve_root(False, data_root)
    chain = _toolchain(home)
    typer.echo(f"route smoke at {label}: {root}")
    preflight = run_preflight(root, REAL_RUN, extra=toolchain.check(chain).checks)
    for line in preflight.lines():
        typer.echo(line)
    if not preflight.ok:
        typer.echo("refusing to run: preflight failed")
        raise typer.Exit(code=1)
    try:
        report = smoke.run_smoke(
            root,
            chain,
            repeats=repeats,
            single_departure=single_departure,
            departure_time=departure,
            echo=typer.echo,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"FAIL {exc}")
        raise typer.Exit(code=1) from exc
    summary = report.to_dict()
    typer.echo(f"smoke: {len(report.records)} run(s): {', '.join(summary['outcomes'])}")
    for record in report.records:
        digest = (record.output or {}).get("canonical_value_sha256")
        typer.echo(
            f"  {record.run_id}: wall {record.wall_seconds} s, peak RSS "
            f"{record.rss.get('peak_rss_bytes', 0) / 10**9:.2f} GB, values {digest}"
        )
    typer.echo(
        f"smoke: outputs {'identical' if report.deterministic else 'DIFFER'} across runs; "
        f"peak RSS {report.peak_rss_bytes / 10**9:.2f} GB "
        f"({'under' if report.under_kill_line else 'AT OR OVER'} the 22 GB kill line)"
    )
    if not report.ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover - `python -m phillysim.cli`
    app()
