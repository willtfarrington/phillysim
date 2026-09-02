"""EP-2 smoke tests: the package imports and the CLI entry point answers."""

from __future__ import annotations

import json

from typer.testing import CliRunner

import phillysim
from phillysim.cli import app

runner = CliRunner()


def test_package_exposes_version() -> None:
    assert isinstance(phillysim.__version__, str)
    assert phillysim.__version__


def test_help_works() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    assert "measures access" in result.output
    assert "version" in result.output
    assert "paths" in result.output


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.output


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == phillysim.__version__


def test_paths_command_json(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PHILLYSIM_DATA_ROOT", str(tmp_path / "root"))
    result = runner.invoke(app, ["paths", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data_root"] == str((tmp_path / "root").resolve())
    assert set(payload["zones"]) == {
        "raw",
        "intermediate",
        "curated",
        "public",
        "quarantine",
        "cache",
    }
    assert not (tmp_path / "root").exists(), "paths must not create directories"
