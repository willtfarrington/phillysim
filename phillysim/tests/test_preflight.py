"""EP-4b preflight tests: all checks reported in one pass; simulated failures refuse the run."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from phillysim.cli import app
from phillysim.preflight import (
    FIXTURE_SCALE,
    GB,
    GIB,
    LOCKED_PACKAGES,
    REAL_RUN,
    Probes,
    Thresholds,
    nearest_existing,
    run_preflight,
)

HEALTHY = Probes(
    free_disk=lambda _path: 500 * GB,
    total_ram=lambda: 64 * GIB,
    package_version=lambda name: "1.0",
    python_version=(3, 13, 0),
    writable=lambda _path: True,
)


def test_thresholds_follow_architecture_budgets() -> None:
    assert REAL_RUN.min_free_disk == 150 * GB
    assert REAL_RUN.min_ram == 24 * GIB
    assert "150 GB" in REAL_RUN.label
    assert FIXTURE_SCALE.min_free_disk < REAL_RUN.min_free_disk
    assert "fixture" in FIXTURE_SCALE.label and "not the real-run budget" in FIXTURE_SCALE.label


def test_healthy_machine_passes_every_check(tmp_path: Path) -> None:
    report = run_preflight(tmp_path, REAL_RUN, HEALTHY)
    assert report.ok
    assert [c.name for c in report.checks] == ["disk", "ram", "python", "packages", "root"]
    assert all(name in report.checks[3].detail for name in LOCKED_PACKAGES)
    assert report.lines()[0].endswith(REAL_RUN.label)
    assert report.lines()[-1] == "preflight: all checks passed"


def test_simulated_failures_are_all_reported_in_one_pass(tmp_path: Path) -> None:
    sick = Probes(
        free_disk=lambda _path: 20 * GB,
        total_ram=lambda: 8 * GIB,
        package_version=lambda name: None if name in {"duckdb", "pyogrio"} else "1.0",
        python_version=(3, 11, 9),
        writable=lambda _path: False,
    )
    report = run_preflight(tmp_path, REAL_RUN, sick)
    assert not report.ok
    assert [c.name for c in report.failed] == ["disk", "ram", "python", "packages", "root"]
    by_name = {c.name: c.detail for c in report.checks}
    assert "20.0 GB free" in by_name["disk"] and "150.0 GB" in by_name["disk"]
    assert "8.6 GB physical RAM" in by_name["ram"]
    assert "3.11.9" in by_name["python"]
    assert by_name["packages"] == "missing: duckdb, pyogrio"
    assert "not writable" in by_name["root"]
    assert report.lines()[-1] == "preflight: 5 check(s) failed"


def test_one_failing_check_is_enough_to_refuse(tmp_path: Path) -> None:
    low_disk = Probes(
        free_disk=lambda _path: 149 * GB,
        total_ram=HEALTHY.total_ram,
        package_version=HEALTHY.package_version,
        python_version=HEALTHY.python_version,
        writable=HEALTHY.writable,
    )
    report = run_preflight(tmp_path, REAL_RUN, low_disk)
    assert [c.name for c in report.failed] == ["disk"]
    assert run_preflight(tmp_path, FIXTURE_SCALE, low_disk).ok, "fixture scale is smaller"


def test_unknown_measurements_fail_rather_than_pass(tmp_path: Path) -> None:
    blind = Probes(
        free_disk=lambda _path: None,
        total_ram=lambda: None,
        package_version=HEALTHY.package_version,
        python_version=HEALTHY.python_version,
        writable=HEALTHY.writable,
    )
    report = run_preflight(tmp_path, Thresholds(1, 1, "tiny"), blind)
    assert [c.name for c in report.failed] == ["disk", "ram"]
    assert "could not determine" in report.checks[0].detail


def test_real_probes_measure_this_machine(tmp_path: Path) -> None:
    report = run_preflight(tmp_path / "not" / "yet" / "created", FIXTURE_SCALE)
    by_name = {c.name: c for c in report.checks}
    assert by_name["disk"].ok and by_name["ram"].ok, [c.detail for c in report.checks]
    assert by_name["python"].ok and by_name["packages"].ok and by_name["root"].ok
    assert nearest_existing(tmp_path / "not" / "yet" / "created") == tmp_path.resolve()


def test_cli_run_refuses_when_preflight_fails(monkeypatch, tmp_path: Path) -> None:
    """The CLI prints every check and exits 1 without touching the data root."""
    from phillysim import cli

    def failing_preflight(root: Path, thresholds: Thresholds):
        sick = Probes(
            free_disk=lambda _p: 0,
            total_ram=lambda: 0,
            package_version=HEALTHY.package_version,
            python_version=HEALTHY.python_version,
            writable=HEALTHY.writable,
        )
        return run_preflight(root, thresholds, sick)

    monkeypatch.setattr(cli, "run_preflight", failing_preflight)
    monkeypatch.setenv("PHILLYSIM_DATA_ROOT", str(tmp_path / "root"))
    result = CliRunner().invoke(app, ["run", "--fixture"])
    assert result.exit_code == 1, result.output
    assert "FAIL disk" in result.output and "FAIL ram" in result.output
    assert "preflight: 2 check(s) failed" in result.output
    assert "refusing to run" in result.output
    assert "fixture scale" in result.output
    assert not (tmp_path / "root").exists(), "a refused run creates nothing"
