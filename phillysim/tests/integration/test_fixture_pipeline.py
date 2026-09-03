"""EP-4b integration suite: tinycity through all eleven stages (the M1 go/no-go evidence).

``phillysim run --fixture`` completes end to end and its curated outputs equal
the committed golden tables by content; a second run skips every stage; a
parameter change re-runs only the dependent stages; an injected mid-stage
failure leaves a state ``verify --fixture`` reports coherently, naming the
incomplete stage, and the next run resumes from it. Offline by construction.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from typer.testing import CliRunner

from phillysim import runner
from phillysim.cli import app
from phillysim.fixtures import pipeline as fx
from phillysim.fixtures.pipeline import FIXTURE_ROOT_NAME, fixture_pipeline
from phillysim.publish.export import PUBLIC_FILES, PUBLIC_MANIFEST
from phillysim.stages import Pipeline, Stage, StageContext, StageError

GOLDEN = {
    "curated/tracts_spine.parquet": "tracts_spine.parquet",
    "curated/sites.parquet": "sites.parquet",
    "curated/travel_times.parquet": "travel_times.parquet",
    "curated/tract_metrics.parquet": "tract_metrics.parquet",
}


def _read(path: Path) -> pd.DataFrame:
    try:
        return gpd.read_parquet(path)
    except ValueError:
        return pd.read_parquet(path)


@pytest.fixture
def cli_env(monkeypatch, tmp_path: Path) -> Path:
    """Point the CLI at a scratch data root; return the fixture root it will use."""
    monkeypatch.setenv("PHILLYSIM_DATA_ROOT", str(tmp_path / "data"))
    return (tmp_path / "data").resolve() / FIXTURE_ROOT_NAME


def test_pipeline_has_eleven_stages_in_architecture_order() -> None:
    pipeline = fixture_pipeline()
    assert len(pipeline) == 11
    assert pipeline.names == (
        "acquire",
        "validate",
        "spine",
        "demographics",
        "destinations",
        "conflate",
        "hours",
        "network",
        "travel_times",
        "metrics",
        "publish",
    )
    zones = [out.split("/")[0] for stage in pipeline for out in stage.outputs]
    assert set(zones) == {"raw", "intermediate", "curated", "public"}


def test_run_fixture_end_to_end_matches_golden_tables(cli_env: Path, tinycity_dir: Path) -> None:
    result = CliRunner().invoke(app, ["run", "--fixture"])
    assert result.exit_code == 0, result.output
    assert "preflight: all checks passed" in result.output
    assert "fixture scale" in result.output
    assert "11 stage(s) ran, 0 skipped" in result.output
    for rel, golden in GOLDEN.items():
        pd.testing.assert_frame_equal(
            _read(cli_env / rel), _read(tinycity_dir / "expected" / golden)
        )
    # EP-7: the public zone is complete, labeled, and the gate verb is green on it.
    assert sorted(p.name for p in (cli_env / "public").iterdir()) == sorted(
        [*PUBLIC_FILES, PUBLIC_MANIFEST]
    )
    gate = CliRunner().invoke(app, ["gate", "--fixture"])
    assert gate.exit_code == 0, gate.output
    assert "publish gate: green (4 file(s) labeled, 8 source(s)" in gate.output
    assert "Bucket B (ODbL-1.0), 6 row(s)" in gate.output
    assert "Bucket B (ODbL-1.0), 13 row(s)" in gate.output
    validation = json.loads((cli_env / "intermediate" / "validation.json").read_text("utf-8"))
    assert set(validation) == set(fx.SOURCES)
    assert all(entry["violations"] == [] for entry in validation.values())
    assert not any((cli_env / "quarantine").iterdir()), "nothing quarantined on the valid fixture"

    second = CliRunner().invoke(app, ["run", "--fixture"])
    assert second.exit_code == 0, second.output
    assert "0 stage(s) ran, 11 skipped" in second.output

    status = CliRunner().invoke(app, ["status", "--fixture"])
    assert status.exit_code == 0, status.output
    assert "11 fresh, 0 stale, 0 missing, 0 incomplete" in status.output

    verify = CliRunner().invoke(app, ["verify", "--fixture"])
    assert verify.exit_code == 0, verify.output
    assert "8 of 8 snapshot(s) verified" in verify.output
    assert "11 of 11 stage(s) done and intact" in verify.output


def test_parameter_change_reruns_only_dependent_stages(cli_env: Path) -> None:
    assert CliRunner().invoke(app, ["run", "--fixture"]).exit_code == 0
    result = CliRunner().invoke(
        app, ["run", "--fixture", "--param", "metrics.methods_version=tinycity-fixture-2"]
    )
    assert result.exit_code == 0, result.output
    assert "2 stage(s) ran, 9 skipped" in result.output
    assert "run  metrics" in result.output and "run  publish" in result.output
    metrics = pd.read_parquet(cli_env / "curated" / "tract_metrics.parquet")
    assert set(metrics["methods_version"]) == {"tinycity-fixture-2"}
    manifest = json.loads((cli_env / "public" / PUBLIC_MANIFEST).read_text("utf-8"))
    assert manifest["methods_version"] == "tinycity-fixture-2"

    # A censoring change re-runs the matrix and the metrics; publish is skipped when the
    # metrics content is unchanged (every nearest site is under 30 minutes).
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--fixture",
            "--param",
            "travel_times.censor_min=30",
            "--param",
            "metrics.methods_version=tinycity-fixture-2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "run  travel_times" in result.output and "run  metrics" in result.output
    assert "skip publish" in result.output
    matrix = pd.read_parquet(cli_env / "curated" / "travel_times.parquet")
    assert matrix["time_p85_min"].max() == 30.0

    bad = CliRunner().invoke(app, ["run", "--fixture", "--param", "metrics.nope=1"])
    assert bad.exit_code != 0 and "no parameter" in bad.output


def test_run_through_a_stage_and_status_of_the_rest(cli_env: Path) -> None:
    result = CliRunner().invoke(app, ["run", "--fixture", "--stage", "spine"])
    assert result.exit_code == 0, result.output
    assert "3 stage(s) ran" in result.output
    status = CliRunner().invoke(app, ["status", "--fixture"])
    assert "3 fresh, 0 stale, 8 missing, 0 incomplete" in status.output
    assert CliRunner().invoke(app, ["run", "--fixture", "--stage", "nope"]).exit_code != 0


def test_injected_failure_then_verify_names_the_stage_and_run_resumes(cli_env: Path) -> None:
    calls = {"n": 0}
    original = fixture_pipeline()

    def failing_hours(ctx: StageContext) -> None:
        calls["n"] += 1
        ctx.output(fx.SITES).write_bytes(b"partial parquet")  # staging only
        if calls["n"] == 1:
            raise RuntimeError("injected mid-stage failure")
        fx.hours(ctx)

    stages = [
        Stage(s.name, failing_hours, s.inputs, s.outputs, s.params) if s.name == "hours" else s
        for s in original
    ]
    broken = Pipeline(original.name, stages)
    cli_env.parent.mkdir(parents=True)
    with pytest.raises(StageError, match="injected mid-stage failure"):
        runner.run(cli_env, broken)
    assert not (cli_env / fx.SITES).exists(), "no partial output in the curated zone"
    assert (cli_env / fx.SITES_CONFLATED).exists()

    verify = CliRunner().invoke(app, ["verify", "--fixture"])
    assert verify.exit_code == 1, verify.output
    assert "8 of 8 snapshot(s) verified" in verify.output
    assert (
        "stage hours: incomplete (failed: RuntimeError: injected mid-stage failure)"
        in verify.output
    )
    assert "6 of 11 stage(s) done and intact; incomplete: hours" in verify.output
    assert "coherence problem" not in verify.output

    status = CliRunner().invoke(app, ["status", "--fixture"])
    assert "incomplete hours" in status.output
    assert "6 fresh, 0 stale, 4 missing, 1 incomplete" in status.output

    resumed = CliRunner().invoke(app, ["run", "--fixture"])
    assert resumed.exit_code == 0, resumed.output
    assert "5 stage(s) ran, 6 skipped" in resumed.output
    assert "run  hours" in resumed.output
    assert CliRunner().invoke(app, ["verify", "--fixture"]).exit_code == 0


def test_invalid_variant_is_quarantined_at_acquire(cli_env: Path) -> None:
    result = CliRunner().invoke(app, ["run", "--fixture", "--param", "acquire.variant=invalid"])
    assert result.exit_code == 1, result.output
    assert "quarantined" in result.output
    assert (cli_env / "quarantine" / "snap_retailers").is_dir()
    assert not (cli_env / "raw").exists() or not any((cli_env / "raw").iterdir())
    verify = CliRunner().invoke(app, ["verify", "--fixture"])
    assert verify.exit_code == 1
    status = CliRunner().invoke(app, ["status", "--fixture"])
    assert "incomplete acquire" in status.output


def test_tampered_output_is_reported_by_verify_and_remade_by_run(cli_env: Path) -> None:
    assert CliRunner().invoke(app, ["run", "--fixture"]).exit_code == 0
    target = cli_env / fx.NETWORK
    target.write_text(target.read_text("utf-8") + "\n", "utf-8")
    verify = CliRunner().invoke(app, ["verify", "--fixture"])
    assert verify.exit_code == 1, verify.output
    assert (
        "FAIL stage network: broken (output intermediate/network.json was altered" in verify.output
    )
    result = CliRunner().invoke(app, ["run", "--fixture"])
    assert result.exit_code == 0, result.output
    assert "run  network" in result.output
    assert "skip travel_times" in result.output, "re-made network.json has identical content"
    assert CliRunner().invoke(app, ["verify", "--fixture"]).exit_code == 0


def test_verbs_without_a_fixture_root_create_nothing(cli_env: Path) -> None:
    status = CliRunner().invoke(app, ["status", "--fixture"])
    assert status.exit_code == 1 and "does not exist" in status.output
    verify = CliRunner().invoke(app, ["verify", "--fixture"])
    assert verify.exit_code == 1 and "nothing to verify" in verify.output
    gate = CliRunner().invoke(app, ["gate", "--fixture"])
    assert gate.exit_code == 1 and "no public zone to check" in gate.output
    assert not cli_env.exists() and not cli_env.parent.exists()


def test_gate_verb_reports_violations_and_gates_a_bare_directory(cli_env: Path) -> None:
    assert CliRunner().invoke(app, ["run", "--fixture", "--stage", "metrics"]).exit_code == 0
    assert CliRunner().invoke(app, ["gate", "--fixture"]).exit_code == 1, "public zone empty"
    assert CliRunner().invoke(app, ["run", "--fixture"]).exit_code == 0
    public = cli_env / "public"
    (public / "stray.txt").write_text("stray", "utf-8")
    gate = CliRunner().invoke(app, ["gate", "--fixture"])
    assert gate.exit_code == 1, gate.output
    assert "FAIL unlisted file(s) in the public zone: ['stray.txt']" in gate.output
    assert "nothing here may be published" in gate.output
    (public / "stray.txt").unlink()
    alone = CliRunner().invoke(app, ["gate", "--public", str(public)])
    assert alone.exit_code == 0, alone.output
    both = CliRunner().invoke(app, ["gate", "--fixture", "--public", str(public)])
    assert both.exit_code != 0 and "mutually exclusive" in both.output
    # The `verify` verb sees the stray file too: the zone is a stage output.
    (public / "stray.txt").write_text("stray", "utf-8")
    assert CliRunner().invoke(app, ["verify", "--fixture"]).exit_code == 1


def test_real_pipeline_verbs_need_a_data_root(cli_env: Path) -> None:
    """Without --fixture the verbs address the real pipeline (EP-5a); with no data root yet
    they report that and create nothing (``run`` is not invoked: it would reach the network)."""
    status = CliRunner().invoke(app, ["status"])
    assert status.exit_code == 1 and "pipeline 'real'" in status.output
    assert "does not exist" in status.output
    verify = CliRunner().invoke(app, ["verify"])
    assert verify.exit_code == 1 and "nothing to verify" in verify.output
    assert not cli_env.parent.exists()


def test_explicit_data_root_option(tmp_path: Path) -> None:
    root = tmp_path / "elsewhere"
    result = CliRunner().invoke(app, ["run", "--fixture", "--data-root", str(root)])
    assert result.exit_code == 0, result.output
    assert (root / runner.STATE_FILE).is_file()
    assert CliRunner().invoke(app, ["verify", "--fixture", "--data-root", str(root)]).exit_code == 0
    state = json.loads((root / runner.STATE_FILE).read_text("utf-8"))
    text = json.dumps(state)
    assert str(root) not in text and root.as_posix() not in text
