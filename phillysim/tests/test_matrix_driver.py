"""EP-14: the matrix driver on scripted children (no JVM): a night's records, the matrix in
the dictionary's shape and its sanity counts, resume (completed runs skipped, an interrupted
or failed run re-run with the attempt kept), the kill handling (a core run killed at the RSS
line or a core wall over the limit -> KILLED-BY-EVIDENCE, stop unless --continue-after-kill;
a non-core kill recorded and the night goes on), the outcome code, the rehearsal's
extrapolation, the read-only status, and the CLI's surface.
"""

from __future__ import annotations

import io
import json
import os
import sys
import textwrap
import zipfile
from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

from phillysim.cli import app
from phillysim.routing import harness, matrix, records
from phillysim.routing.matrix import (
    FINISHED,
    KILLED_BY_EVIDENCE,
    MATRIX_COLUMNS,
    MATRIX_FILE,
    MATRIX_INFO_FILE,
    NIGHT_FILE,
    STOPPED,
    Night,
    matrix_from_output,
    run_matrix,
    sanity_counts,
    status,
    status_lines,
    write_matrix,
)
from phillysim.routing.plan import DEFAULT_PLAN, PLANS_DIR, MatrixPlan, PlanError, parse_plan
from phillysim.routing.toolchain import JAR_NAME, Toolchain

MIB = 1024**2
runner_cli = CliRunner()

# --- a data root, a toolchain, a small plan --------------------------------------------------


def feed_zip(path: Path, start: str, end: str) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as feed:
        feed.writestr(
            "feed_info.txt",
            f"feed_publisher_name,feed_start_date,feed_end_date,feed_version\nSEPTA,{start},{end},v\n",
        )
    path.write_bytes(buffer.getvalue())


@pytest.fixture
def roots(tmp_path: Path) -> tuple[Path, Toolchain]:
    data_root = tmp_path / "data"
    (data_root / "curated").mkdir(parents=True)
    geoids = [f"4210100{i:04d}" for i in range(8)]
    pd.DataFrame(
        {
            "geoid": geoids,
            "centroid_lon": [-75.1 - i * 0.01 for i in range(8)],
            "centroid_lat": [39.9 + i * 0.01 for i in range(8)],
        }
    ).to_parquet(data_root / "curated" / "tracts_spine.parquet", index=False)
    pd.DataFrame(
        {
            "site_id": [f"snap_retailers:10000{i}" for i in range(5)],
            "longitude": [-75.2 + i * 0.01 for i in range(5)],
            "latitude": [39.95 - i * 0.01 for i in range(5)],
        }
    ).to_parquet(data_root / "curated" / "snap_retailers.parquet", index=False)
    network = data_root / "intermediate" / "network"
    network.mkdir(parents=True)
    (network / "clip.osm.pbf").write_bytes(b"pbf" * 100)
    feed_zip(network / "google_bus.zip", "20260906", "20270220")
    feed_zip(network / "google_rail.zip", "20260906", "20261017")
    (data_root / "intermediate" / "network.json").write_text(
        json.dumps(
            {"osm": {"file": "clip.osm.pbf"}, "gtfs": {"google_bus.zip": {}, "google_rail.zip": {}}}
        ),
        "utf-8",
    )
    home = tmp_path / "phillysim"
    home.mkdir()
    chain = Toolchain(home, "windows")
    chain.record_path.write_text(
        json.dumps(
            {
                "jdk": {"release": "jdk-21.0.12.1+1", "version": "21.0.12.1", "sha256": "f9"},
                "jar": {"release": "v7.5.1-r5py", "name": JAR_NAME, "sha256": "d5"},
            }
        ),
        "utf-8",
    )
    return data_root, chain


def small_plan(**overrides) -> MatrixPlan:
    raw = json.loads((PLANS_DIR / DEFAULT_PLAN).read_text("utf-8"))
    raw["name"] = "test-plan"
    raw["origins"]["count"] = 8
    raw["destinations"]["count"] = 5
    raw["rehearsal_origins"] = ["42101000005", "42101000002", "42101000007"]
    raw["runs"] = [
        r
        for r in raw["runs"]
        if r["name"] in ("walk-48-wed", "transit-48-wed", "walk-48-wed-repeat", "transit-30-wed")
    ]
    raw.update(overrides)
    return parse_plan(raw, source="test-plan.json", sha256="ab" * 32)


# --- scripted children ---------------------------------------------------------------------

MATRIX_CHILD = textwrap.dedent(
    """
    import json, math, os, sys, time
    from datetime import UTC, datetime
    from pathlib import Path
    import pandas as pd
    from phillysim.routing import records
    run_dir = Path(sys.argv[1])
    plan = json.loads((run_dir / "plan.json").read_text("utf-8"))
    assert plan["snap_to_network"] is True
    assert os.environ["JAVA_HOME"].endswith("jdk-21.0.12.1+1")
    now = lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    phases = {"import": {"start": now(), "end": now()},
              "build": {"start": now(), "end": now(), "network_cached_before": True}}
    drop = os.environ.get("TEST_MATRIX_DROP")
    rows = []
    for mode in plan["modes"]:
        phases["route:" + mode] = {"start": now()}
        for o in plan["origins"]["points"]:
            for d in plan["destinations"]["points"]:
                if drop and d["id"] == drop:
                    continue
                h = (int(o["id"][-3:]) * 7 + int(d["id"][-1]) * 13 + (5 if mode == "walk" else 0))
                v = int(h * plan["speed_walking_kmh"]) % 140
                p50 = float("nan") if v > 120 else float(v)
                p85 = p50 if math.isnan(p50) else min(p50 + 3.0, 120.0)
                rows.append({"mode": mode, "from_id": o["id"], "to_id": d["id"],
                             "travel_time_p50": p50, "travel_time_p85": p85})
        phases["route:" + mode]["end"] = now()
        phases["route:" + mode]["rows"] = len(rows)
    records.write_output(pd.DataFrame(rows), run_dir / records.OUTPUT_FILE)
    (run_dir / records.PHASES_FILE).write_text(json.dumps(phases), "utf-8")
    print("child: routed", plan["slug"], flush=True)
    """
)

FAILING_CHILD = textwrap.dedent(
    """
    import json, sys
    from pathlib import Path
    run_dir = Path(sys.argv[1])
    (run_dir / "error.json").write_text(json.dumps({"type": "RuntimeError",
        "message": "boom at " + str(run_dir.parents[3]), "traceback": "..."}))
    sys.exit(1)
    """
)

HUNGRY_CHILD = textwrap.dedent(
    """
    import time
    blocks = []
    for _ in range(60):
        b = bytearray(16 * 1024 * 1024)
        for i in range(0, len(b), 4096):
            b[i] = 1
        blocks.append(b)
        time.sleep(0.02)
    time.sleep(30)
    """
)


def scripted(script: str):
    return lambda run_dir: [sys.executable, "-c", script, str(run_dir)]


def make_runner(children: dict[str, str] | None = None, **kwargs):
    """A runner that is ``harness.run`` on a scripted child chosen by the run's slug."""
    children = children or {}

    def runner(plan, **run_kwargs):
        script = children.get(plan.slug, MATRIX_CHILD)
        return harness.run(
            plan,
            command=scripted(script),
            interval=0.05,
            kill_bytes=kwargs.get("kill_bytes", 400 * MIB),
            budget_bytes=kwargs.get("budget_bytes", 300 * MIB),
            **run_kwargs,
        )

    return runner


def night_json(directory: Path) -> dict:
    return json.loads((directory / NIGHT_FILE).read_text("utf-8"))


# --- the whole night ------------------------------------------------------------------------


def test_a_night_finishes_with_records_matrices_and_sanity_counts(roots) -> None:
    data_root, chain = roots
    plan = small_plan()
    lines: list[str] = []
    night = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        night_id_="20260903T230000Z-test-plan",
        runner=make_runner(),
        echo=lines.append,
    )
    assert night.state == FINISHED and night.data["outcome_code"] is None
    assert night.dir == data_root / "runs" / "routing" / "20260903T230000Z-test-plan"
    saved = night_json(night.dir)
    assert saved["schema_version"] == 1 and saved["night_id"] == night.id
    assert saved["plan"]["runs"] == list(plan.run_names) and saved["plan"]["sha256"] == "ab" * 32
    assert saved["origins"]["count"] == 8 and saved["destinations"]["count"] == 5
    assert saved["points"]["file"] == "points.parquet" and (night.dir / "points.parquet").is_file()
    assert saved["feeds"]["gtfs_rail"]["feed_end_date"] == "2026-10-17"
    assert saved["inputs"]["osm"] == "intermediate/network/clip.osm.pbf"
    assert saved["all_runs_done"] and saved["finished_at"] and saved["expected_wall"] is None
    assert [e["status"] for e in saved["runs"].values()] == ["completed"] * 4
    assert {n: e["order"] for n, e in saved["runs"].items()} == {
        "walk-48-wed": 1,
        "transit-48-wed": 2,
        "walk-48-wed-repeat": 3,
        "transit-30-wed": 4,
    }
    core = (
        saved["runs"]["walk-48-wed"]["wall_seconds"]
        + saved["runs"]["transit-48-wed"]["wall_seconds"]
    )
    assert saved["core_wall_seconds"] == pytest.approx(core, abs=0.01)
    assert saved["core_wall_within_limit"] is True and saved["core_wall_limit_seconds"] == 28_800
    assert saved["peak_rss_bytes"] > 0 and saved["peak_rss_run"] in saved["runs"]
    assert len(saved["driver"]["invocations"]) == 1 and saved["driver"]["pid"]
    assert saved["driver"]["invocations"][0]["resumed"] is False
    # Every run directory holds EP-13's files plus the matrix and its digests.
    for name, entry in saved["runs"].items():
        run_dir = night.dir / entry["dir"]
        assert entry["dir"] == name and entry["attempts"] == 1
        assert (run_dir / records.RECORD_FILE).is_file() and (run_dir / MATRIX_FILE).is_file()
        info = json.loads((run_dir / MATRIX_INFO_FILE).read_text("utf-8"))
        assert info["matrix"] == entry["matrix"] and info["sanity"] == entry["sanity"]
        assert entry["matrix"]["rows"] == 40 and entry["matrix"]["key"] == list(matrix.MATRIX_KEY)
        assert entry["run_id"] == f"{night.id}/{name}"
        assert entry["phases"]["network_cached_before"] is True
        assert entry["phases"]["route_seconds"] is not None
        frame = pd.read_parquet(run_dir / MATRIX_FILE)
        assert list(frame.columns) == list(MATRIX_COLUMNS)
        assert frame["mode"].unique().tolist() == [entry["mode"]]
        assert frame["time_median_min"].max() <= 120 and not frame["time_median_min"].isna().any()
        assert frame["time_p85_min"].between(0, 120).all()
        assert frame.equals(frame.sort_values(list(matrix.MATRIX_KEY)).reset_index(drop=True))
        sanity = entry["sanity"]
        assert sanity["pairs_expected"] == 40 and sanity["rows"] == 40
        assert sanity["finite_pairs"] + sanity["at_censor"] == 40
        assert sanity["finite_share"] == pytest.approx(sanity["finite_pairs"] / 40)
        assert sanity["finite_share_gate"] == 0.95
        assert (frame["time_median_min"] < 120).sum() == sanity["finite_pairs"]
    # The repeat reproduces the original: both digests equal; the sensitivity run differs.
    runs = saved["runs"]
    for digest in ("byte_sha256", "canonical_value_sha256"):
        assert runs["walk-48-wed"]["matrix"][digest] == runs["walk-48-wed-repeat"]["matrix"][digest]
        assert runs["walk-48-wed"]["output"][digest] == runs["walk-48-wed-repeat"]["output"][digest]
        assert runs["transit-48-wed"]["matrix"][digest] != runs["transit-30-wed"]["matrix"][digest]
    # Nothing in the night record names the data root or the project directory.
    text = (night.dir / NIGHT_FILE).read_text("utf-8")
    assert str(data_root) not in text and data_root.as_posix() not in text
    assert str(chain.home) not in text and chain.home.as_posix() not in text
    log = (night.dir / matrix.DRIVER_LOG).read_text("utf-8")
    assert "starting plan test-plan" in log and f"night {night.id}: finished" in log
    assert any("walk-48-wed: matrix 40 rows" in line for line in lines)


def test_a_dropped_destination_is_censored_and_counted(roots, monkeypatch) -> None:
    data_root, chain = roots
    monkeypatch.setenv("TEST_MATRIX_DROP", "snap_retailers:100003")
    plan = small_plan()
    night = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        only=["walk-48-wed"],
        runner=make_runner(),
    )
    entry = night.runs["walk-48-wed"]
    assert entry["sanity"]["rows"] == 32 and entry["sanity"]["missing_rows"] == 8
    assert entry["matrix"]["rows"] == 40  # the grid is complete; the dropped pairs read 120
    frame = pd.read_parquet(night.dir / "walk-48-wed" / MATRIX_FILE)
    dropped = frame[frame["site_id"] == "snap_retailers:100003"]
    assert len(dropped) == 8 and (dropped["time_median_min"] == 120).all()
    assert night.state == STOPPED and "runs pending" in night.data["stop_reason"]


# --- resume ---------------------------------------------------------------------------------


def test_resume_skips_completed_runs_and_reruns_an_interrupted_one(roots) -> None:
    data_root, chain = roots
    plan = small_plan()
    first = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        night_id_="n1",
        only=["walk-48-wed", "transit-48-wed"],
        runner=make_runner(),
    )
    assert first.state == STOPPED and first.data["core_wall_within_limit"] is True
    # Simulate a driver that died mid-run: the third run's status reads "running" and its
    # directory holds a half-written attempt.
    data = night_json(first.dir)
    data["runs"]["walk-48-wed-repeat"].update(
        status="running", attempts=1, started_at="2026-09-01T00:00:00Z"
    )
    (first.dir / NIGHT_FILE).write_text(json.dumps(data), "utf-8")
    (first.dir / "walk-48-wed-repeat").mkdir()
    (first.dir / "walk-48-wed-repeat" / "plan.json").write_text("{}", "utf-8")
    lines: list[str] = []
    second = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        night_id_="n1",
        runner=make_runner(),
        echo=lines.append,
    )
    assert second.state == FINISHED
    saved = night_json(second.dir)
    assert saved["runs"]["walk-48-wed"]["attempts"] == 1  # skipped, not re-run
    assert saved["runs"]["walk-48-wed-repeat"]["attempts"] == 2
    assert saved["runs"]["walk-48-wed-repeat"]["earlier_attempts"] == [
        "walk-48-wed-repeat.attempt1"
    ]
    assert (second.dir / "walk-48-wed-repeat.attempt1" / "plan.json").is_file()
    assert (second.dir / "walk-48-wed-repeat" / MATRIX_FILE).is_file()
    assert saved["interruptions"][0]["run"] == "walk-48-wed-repeat"
    assert [i["resumed"] for i in saved["driver"]["invocations"]] == [False, True]
    assert any("completed earlier" in line and "walk-48-wed" in line for line in lines)
    assert "resuming plan test-plan" in (second.dir / matrix.DRIVER_LOG).read_text("utf-8")


def test_resume_refuses_a_different_plan_or_subset(roots) -> None:
    data_root, chain = roots
    run_matrix(
        small_plan(),
        data_root=data_root,
        toolchain=chain,
        night_id_="n2",
        only=["walk-48-wed"],
        runner=make_runner(),
    )
    other = parse_plan(
        json.loads(json.dumps(small_plan().to_dict())), source="x.json", sha256="cd" * 32
    )
    with pytest.raises(PlanError, match="different plan file"):
        run_matrix(
            other, data_root=data_root, toolchain=chain, night_id_="n2", runner=make_runner()
        )
    with pytest.raises(PlanError, match="origins subset"):
        run_matrix(
            small_plan(),
            data_root=data_root,
            toolchain=chain,
            night_id_="n2",
            origins_subset=3,
            runner=make_runner(),
        )


def test_a_failed_run_stops_the_night_and_a_resume_reruns_it(roots) -> None:
    data_root, chain = roots
    plan = small_plan()
    night = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        night_id_="n3",
        runner=make_runner({"transit-48-wed": FAILING_CHILD}),
    )
    assert night.state == STOPPED and night.data["outcome_code"] is None
    assert night.data["stop_reason"].startswith(
        "run transit-48-wed failed: RuntimeError: boom at <data-root>"
    )
    statuses = {n: e["status"] for n, e in night.runs.items()}
    assert statuses == {
        "walk-48-wed": "completed",
        "transit-48-wed": "failed",
        "walk-48-wed-repeat": "pending",
        "transit-30-wed": "pending",
    }
    resumed = run_matrix(
        plan, data_root=data_root, toolchain=chain, night_id_="n3", runner=make_runner()
    )
    assert resumed.state == FINISHED and resumed.data["stop_reason"] is None
    assert resumed.runs["transit-48-wed"]["attempts"] == 2
    assert (resumed.dir / "transit-48-wed.attempt1" / records.ERROR_FILE).is_file()
    assert resumed.runs["transit-48-wed"]["wall_seconds"] > 0  # the completed attempt's own wall


# --- kills and the outcome code -------------------------------------------------------------


def test_a_core_kill_marks_the_night_killed_by_evidence_and_stops(roots) -> None:
    data_root, chain = roots
    plan = small_plan()
    night = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        night_id_="n4",
        runner=make_runner({"transit-48-wed": HUNGRY_CHILD}),
    )
    assert night.state == KILLED_BY_EVIDENCE == night.data["outcome_code"]
    assert "core run transit-48-wed killed at the RSS line" in night.data["kill_reason"]
    assert night.runs["transit-48-wed"]["status"] == "killed-rss"
    assert night.runs["walk-48-wed-repeat"]["status"] == "pending"
    assert night.data["finished_at"] and not night.data["all_runs_done"]
    assert night.data["core_wall_within_limit"] is None  # not both core runs completed
    # Re-invoked without the flag: nothing runs, the state stands.
    lines: list[str] = []
    again = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        night_id_="n4",
        runner=make_runner(),
        echo=lines.append,
    )
    assert (
        again.state == KILLED_BY_EVIDENCE
        and again.runs["walk-48-wed-repeat"]["status"] == "pending"
    )
    assert any("not continuing without --continue-after-kill" in line for line in lines)
    assert len(again.data["driver"]["invocations"]) == 1
    # With the owner's flag: the remaining runs execute; the killed core run is not re-run.
    cont = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        night_id_="n4",
        continue_after_kill=True,
        runner=make_runner(),
    )
    assert cont.state == KILLED_BY_EVIDENCE and cont.data["outcome_code"] == KILLED_BY_EVIDENCE
    assert (
        cont.runs["transit-48-wed"]["status"] == "killed-rss"
        and cont.runs["transit-48-wed"]["attempts"] == 1
    )
    assert cont.runs["walk-48-wed-repeat"]["status"] == "completed"
    assert cont.runs["transit-30-wed"]["status"] == "completed"
    assert cont.data["all_runs_done"] and cont.data["continue_after_kill"] is True


def test_a_non_core_kill_is_recorded_and_the_night_goes_on(roots) -> None:
    data_root, chain = roots
    night = run_matrix(
        small_plan(),
        data_root=data_root,
        toolchain=chain,
        night_id_="n5",
        runner=make_runner({"walk-48-wed-repeat": HUNGRY_CHILD}),
    )
    assert night.state == FINISHED and night.data["outcome_code"] is None
    assert night.runs["walk-48-wed-repeat"]["status"] == "killed-rss"
    assert night.runs["transit-30-wed"]["status"] == "completed"
    assert night.data["peak_rss_run"] == "walk-48-wed-repeat"
    assert night.data["peak_rss_bytes"] >= 400 * MIB


def test_a_core_wall_over_the_limit_is_killed_by_evidence(roots) -> None:
    data_root, chain = roots
    plan = small_plan(core_wall_limit_hours=1e-7)  # 0.36 ms: any run exceeds it
    night = run_matrix(
        plan, data_root=data_root, toolchain=chain, night_id_="n6", runner=make_runner()
    )
    assert night.state == KILLED_BY_EVIDENCE
    assert (
        night.data["kill_reason"].startswith("core wall")
        and "after walk-48-wed" in night.data["kill_reason"]
    )
    assert night.runs["walk-48-wed"]["status"] == "completed"
    assert night.runs["transit-48-wed"]["status"] == "pending"
    cont = run_matrix(
        plan,
        data_root=data_root,
        toolchain=chain,
        night_id_="n6",
        continue_after_kill=True,
        runner=make_runner(),
    )
    assert cont.state == KILLED_BY_EVIDENCE and cont.data["all_runs_done"]
    assert cont.data["core_wall_within_limit"] is False


# --- the rehearsal's extrapolation ----------------------------------------------------------


def test_a_subset_night_extrapolates_linearly_in_origins(roots) -> None:
    data_root, chain = roots
    plan = small_plan()
    night = run_matrix(
        plan, data_root=data_root, toolchain=chain, origins_subset=3, runner=make_runner()
    )
    assert night.id.endswith("-test-plan-subset3") and night.state == FINISHED
    assert night.data["origins"] == {
        "count": 3,
        "full_count": 8,
        "subset": 3,
        "description": plan.origins.description,
        "table": "curated/tracts_spine.parquet",
    }
    points = pd.read_parquet(night.dir / "points.parquet")
    assert list(points.loc[points["role"] == "origin", "id"]) == list(plan.rehearsal_origins)
    assert night.runs["walk-48-wed"]["matrix"]["rows"] == 15
    expected = night.data["expected_wall"]
    assert expected["subset_origins"] == 3 and expected["full_origins"] == 8
    assert "linear in origins" in expected["method"]
    for name, run in expected["runs"].items():
        entry = night.runs[name]
        assert run["wall_seconds"] == entry["wall_seconds"]
        assert run["per_origin_seconds"] == pytest.approx(run["route_seconds"] / 3, abs=1e-3)
        assert run["extrapolated_seconds"] == pytest.approx(
            run["fixed_seconds"] + run["per_origin_seconds"] * 8, abs=0.2
        )
    assert expected["core_extrapolated_seconds"] == pytest.approx(
        expected["runs"]["walk-48-wed"]["extrapolated_seconds"]
        + expected["runs"]["transit-48-wed"]["extrapolated_seconds"],
        abs=0.2,
    )
    assert expected["core_within_limit"] is True and expected["core_wall_limit_seconds"] == 28_800
    assert expected["all_runs_extrapolated_seconds"] is not None  # 0 when the child is instant
    assert any(
        "extrapolated core wall at 8 origins" in line for line in status_lines(status(night.dir))
    )


# --- refusals ----------------------------------------------------------------------------------


def test_the_driver_refuses_dates_outside_a_feed_window_before_creating_a_night(roots) -> None:
    data_root, chain = roots
    feed_zip(data_root / "intermediate" / "network" / "google_rail.zip", "20260906", "20260920")
    with pytest.raises(
        PlanError, match="outside a feed's authoritative window.*gtfs_rail: 2026-09-23"
    ):
        run_matrix(
            small_plan(), data_root=data_root, toolchain=chain, night_id_="n7", runner=make_runner()
        )
    assert not (data_root / "runs" / "routing" / "n7").exists()


def test_the_driver_refuses_an_unknown_only_run(roots) -> None:
    data_root, chain = roots
    with pytest.raises(PlanError, match="not in the plan"):
        run_matrix(
            small_plan(), data_root=data_root, toolchain=chain, only=["nope"], runner=make_runner()
        )


# --- the matrix shape and the sanity counts (unit) -----------------------------------------


def test_matrix_from_output_censors_and_completes_the_grid(tmp_path: Path) -> None:
    raw = pd.DataFrame(
        {
            "mode": ["walk", "walk", "walk", "walk_transit"],
            "from_id": ["o1", "o1", "o2", "o1"],
            "to_id": ["d1", "d2", "d1", "d1"],
            "travel_time_p50": [10.0, float("nan"), 120.0, 5.0],
            "travel_time_p85": [12.0, float("nan"), 125.0, 6.0],
        }
    )
    frame = matrix_from_output(raw, ["o2", "o1"], ["d2", "d1"], "walk", 120)
    assert list(frame.columns) == list(MATRIX_COLUMNS)
    assert frame[["origin_geoid", "site_id"]].values.tolist() == [
        ["o1", "d1"],
        ["o1", "d2"],
        ["o2", "d1"],
        ["o2", "d2"],
    ]
    assert frame["time_median_min"].tolist() == [10.0, 120.0, 120.0, 120.0]
    assert frame["time_p85_min"].tolist() == [
        12.0,
        120.0,
        120.0,
        120.0,
    ]  # 125 clipped, missing censored
    assert (frame["mode"] == "walk").all()
    counts = sanity_counts(raw, ["o1", "o2"], ["d1", "d2"], "walk", 120)
    assert counts["pairs_expected"] == 4 and counts["rows"] == 3 and counts["missing_rows"] == 1
    assert counts["unreachable"] == 1 and counts["finite_pairs"] == 1 and counts["at_censor"] == 3
    assert counts["finite_share"] == 0.25 and counts["finite_share_gate_met"] is False
    assert counts["origins_without_a_finite_pair"] == 1 and counts[
        "origins_without_a_finite_pair_ids"
    ] == ["o2"]
    assert counts["median_minutes"]["min"] == 10.0 and counts["p85_minus_median_mean"] == 2.0
    with pytest.raises(ValueError, match="repeats"):
        matrix_from_output(pd.concat([raw, raw]), ["o1"], ["d1"], "walk", 120)
    # The Parquet is byte-deterministic for value-identical frames.
    a = write_matrix(frame, tmp_path / "a.parquet")
    b = write_matrix(
        frame.sample(frac=1, random_state=1)
        .sort_values(list(matrix.MATRIX_KEY))
        .reset_index(drop=True),
        tmp_path / "b.parquet",
    )
    assert (
        a["byte_sha256"] == b["byte_sha256"]
        and a["canonical_value_sha256"] == b["canonical_value_sha256"]
    )
    assert a["rows"] == 4 and a["columns"] == list(MATRIX_COLUMNS)


# --- status (read-only) and the CLI -----------------------------------------------------------


def test_status_reports_the_driver_the_runs_and_the_last_sample(roots) -> None:
    data_root, chain = roots
    night = run_matrix(
        small_plan(),
        data_root=data_root,
        toolchain=chain,
        night_id_="n8",
        only=["walk-48-wed"],
        runner=make_runner(),
    )
    report = status(night.dir)
    assert report["night_id"] == "n8" and report["state"] == STOPPED
    assert report["driver_alive"] is True  # this process was the driver
    assert [r["status"] for r in report["runs"]] == ["completed", "pending", "pending", "pending"]
    # A run in progress: its wall so far and the last RSS sample come from the run directory.
    data = night_json(night.dir)
    data["runs"]["transit-48-wed"].update(status="running", started_at="2026-09-01T00:00:00Z")
    data["driver"]["pid"] = 2**22 + 12345  # not a live process
    (night.dir / NIGHT_FILE).write_text(json.dumps(data), "utf-8")
    (night.dir / "transit-48-wed").mkdir()
    (night.dir / "transit-48-wed" / records.RSS_FILE).write_text(
        "utc,elapsed_s,rss_bytes\n2026-09-03T23:00:01Z,1.0,1000\n2026-09-03T23:00:02Z,2.0,3000000000\n",
        "utf-8",
    )
    report = status(night.dir)
    assert report["driver_alive"] is False
    running = report["runs"][1]
    assert running["status"] == "running" and running["wall_seconds"] > 0
    assert running["last_rss"] == {
        "utc": "2026-09-03T23:00:02Z",
        "elapsed_s": 2.0,
        "rss_bytes": 3000000000,
    }
    lines = status_lines(report)
    assert lines[0].startswith("night n8: stopped") and "not running" in lines[0]
    assert any("transit-48-wed" in line and "last sample 3.00 GB" in line for line in lines)
    assert any("core" in line and "walk-48-wed" in line for line in lines)
    # The CLI reads the same report; --night picks a night, the default is the latest.
    result = runner_cli.invoke(
        app, ["route", "status", "--data-root", str(data_root), "--night", "n8"]
    )
    assert result.exit_code == 0, result.output
    assert "night n8: stopped" in result.output
    result = runner_cli.invoke(app, ["route", "status", "--data-root", str(data_root), "--json"])
    assert result.exit_code == 0 and json.loads(result.output)["night_id"] == "n8"
    result = runner_cli.invoke(
        app, ["route", "status", "--data-root", str(data_root), "--night", "nope"]
    )
    assert result.exit_code == 1 and "no night nope" in result.output
    result = runner_cli.invoke(app, ["route", "status", "--data-root", str(data_root / "empty")])
    assert result.exit_code == 1 and "no night under" in result.output


def test_route_matrix_help_and_refusals(tmp_path: Path) -> None:
    result = runner_cli.invoke(app, ["route", "matrix", "--help"])
    assert result.exit_code == 0, result.output
    for option in (
        "--plan",
        "--only",
        "--origins-subset",
        "--night",
        "--continue-after-kill",
        "--keep-awake",
    ):
        assert option in result.output
    result = runner_cli.invoke(
        app, ["route", "matrix", "--plan", "nope.json", "--data-root", str(tmp_path)]
    )
    assert result.exit_code == 1 and "no plan file" in result.output
    result = runner_cli.invoke(
        app,
        ["route", "matrix", "--plan", DEFAULT_PLAN, "--data-root", str(tmp_path), "--night", "a/b"],
    )
    assert result.exit_code == 1 and "plain night ID" in result.output
    assert not (tmp_path / "runs").exists()


def test_night_class_refuses_a_non_empty_directory_without_a_record(tmp_path: Path) -> None:
    (tmp_path / "night").mkdir()
    (tmp_path / "night" / "stray").write_text("x", "utf-8")
    points = pd.DataFrame({"role": ["origin"], "id": ["o"], "lon": [0.0], "lat": [0.0]})
    with pytest.raises(PlanError, match="not empty"):
        Night.create(
            tmp_path / "night",
            small_plan(),
            origins_subset=None,
            points=points,
            inputs={},
            windows={},
            continue_after_kill=False,
            roots={},
        )


def test_touch_cache_and_keep_awake(tmp_path: Path) -> None:
    cache = tmp_path / "cache" / "r5py"
    cache.mkdir(parents=True)
    (cache / "x.transport_network").write_bytes(b"n")
    (cache / "tmp").mkdir()
    target = tmp_path / "intermediate" / "clip.osm.pbf"
    target.parent.mkdir()
    target.write_bytes(b"pbf")
    old = 1_600_000_000
    os.utime(target, (old, old))
    try:
        (cache / "clip.osm.pbf").symlink_to(target)
    except OSError:  # no symlink privilege: the check below still holds on the file
        pass
    assert matrix.touch_cache(tmp_path) == 1  # the symlink is skipped
    assert target.stat().st_mtime == old  # the pipeline's file untouched
    assert matrix.touch_cache(tmp_path / "none") == 0
    assert isinstance(matrix.keep_awake(), bool)
    if sys.platform == "win32":
        assert matrix.keep_awake() is True
        import ctypes

        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)  # release the request
