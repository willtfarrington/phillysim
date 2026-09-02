"""Command-line entry point (``phillysim``).

Plain Typer commands over idempotent, fingerprint-checked stage functions; no
orchestrator (architecture.md, B3-07). Inspection commands (``version``,
``paths``), the fixture generator (``gen-tinycity``), and the pipeline verbs
from the stage runner (EP-4b): ``run`` brings a pipeline up to date (skipping
fresh stages), ``status`` reports every stage as fresh / stale / missing /
incomplete, and ``verify`` checks the raw zone against its manifests (EP-4a)
and the stage state against the zones.

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
        typer.echo(f"{row.status:<11}{row.name:<14}{row.detail}")
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
