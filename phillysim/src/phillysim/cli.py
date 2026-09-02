"""Command-line entry point (``phillysim``).

Pipeline stages arrive as plain Typer commands, ``phillysim <stage>``, from the
manifest-engine packet (EP-4) onward. This module ships only the shell plus two
inspection commands so the entry point, packaging, and config wiring can be
tested before any pipeline logic exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from phillysim import __version__
from phillysim.config import ENV_DATA_ROOT, Settings
from phillysim.fixtures.tinycity import Variant, write_fixture

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
