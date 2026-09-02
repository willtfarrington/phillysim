"""Command-line entry point (``phillysim``).

Pipeline stages arrive as plain Typer commands, ``phillysim <stage>``, from the
stage-runner packet (EP-4b) onward. Today the shell carries inspection commands
(``version``, ``paths``), the fixture generator (``gen-tinycity``), and the
snapshot-level ``verify`` from the manifest engine (EP-4a).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Annotated

import typer

from phillysim import __version__
from phillysim.config import ENV_DATA_ROOT, Settings
from phillysim.fixtures.tinycity import Variant, write_fixture
from phillysim.manifest import verify_raw_zone

app = typer.Typer(
    name="phillysim",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
)


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


@app.command()
def verify(
    fixture: Annotated[
        bool,
        typer.Option(
            "--fixture",
            help="Verify a freshly generated tinycity fixture instead of the data root.",
        ),
    ] = False,
    raw: Annotated[
        Path | None,
        typer.Option("--raw", help="Verify this raw-zone directory instead of the data root's."),
    ] = None,
) -> None:
    """Verify every raw snapshot against its manifest (snapshot level; EP-4b adds stage state).

    Exit status 1 if any snapshot fails or the raw zone holds an entry no manifest vouches for.
    """
    if fixture and raw is not None:
        raise typer.BadParameter("--fixture and --raw are mutually exclusive")
    if fixture:
        with tempfile.TemporaryDirectory(prefix="phillysim-tinycity-") as scratch:
            write_fixture(Path(scratch), Variant.VALID)
            report = verify_raw_zone(Path(scratch) / "raw")
        label = "tinycity fixture (fresh generation)"
    else:
        raw_zone = raw if raw is not None else Settings.load().zone("raw")
        report = verify_raw_zone(raw_zone)
        label = "data root" if raw is None else str(raw)
        if not raw_zone.is_dir():
            typer.echo(f"raw zone not found for {label}: nothing to verify")
            raise typer.Exit(code=1)
    typer.echo(f"verifying raw zone: {label}")
    for line in report.lines():
        typer.echo(line)
    if not report.ok:
        raise typer.Exit(code=1)
