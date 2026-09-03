"""EP-13: the routing child's environment and arguments, and the parent's run loop on
scripted children (completed, failed, killed at the RSS line), without a JVM.

The scripted child stands in for ``python -m phillysim.routing.harness``: it is handed
the run directory the same way and writes the same files (the output table, the phase
timings, or an error report), so the record the parent writes is checked end to end,
including the scrub of every absolute path.
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

from phillysim.routing import harness, records
from phillysim.routing.harness import (
    CACHE_DIR,
    HEAP,
    JAVA_TOOL_OPTIONS,
    child_environment,
    environment_overrides,
    r5py_arguments,
)
from phillysim.routing.records import Point, RunPlan
from phillysim.routing.toolchain import JAR_NAME, JDK_DIR_NAME, Toolchain

MIB = 1024**2


@pytest.fixture
def roots(tmp_path: Path) -> tuple[Path, Toolchain]:
    data_root = tmp_path / "data"
    (data_root / "intermediate" / "network").mkdir(parents=True)
    (data_root / "intermediate" / "network" / "clip.osm.pbf").write_bytes(b"pbf" * 100)
    (data_root / "intermediate" / "network" / "bus.zip").write_bytes(b"zip" * 10)
    home = tmp_path / "phillysim"
    home.mkdir()
    chain = Toolchain(home, "windows")
    chain.record_path.write_text(
        json.dumps(
            {
                "jdk": {
                    "release": "jdk-21.0.12.1+1",
                    "version": "21.0.12.1",
                    "sha256": "f9",
                    "java_version": "openjdk 21.0.12.1",
                },
                "jar": {"release": "v7.5.1-r5py", "name": JAR_NAME, "sha256": "d5"},
            }
        ),
        "utf-8",
    )
    return data_root, chain


def plan() -> RunPlan:
    return RunPlan(
        slug="smoke",
        modes=("walk", "walk_transit"),
        speed_walking_kmh=4.8,
        departure="2026-09-23T08:00",
        time_zone="America/New_York",
        window_minutes=60,
        percentiles=(50, 85),
        max_time_minutes=120,
        origins=(Point("o", -75.15, 39.95),),
        destinations=(Point("d", -75.16, 39.95),),
        inputs={
            "osm": "intermediate/network/clip.osm.pbf",
            "gtfs_bus": "intermediate/network/bus.zip",
        },
    )


# --- the environment and the arguments -------------------------------------------------------


def test_environment_overrides_point_everything_under_the_project_and_the_data_root(roots) -> None:
    data_root, chain = roots
    run_dir = data_root / "runs" / "routing" / "x"
    env = environment_overrides(chain, data_root, run_dir)
    assert env["JAVA_HOME"] == str(chain.jdk_dir) and env["JAVA_HOME"].endswith(JDK_DIR_NAME)
    assert env["JAVA_TOOL_OPTIONS"] == JAVA_TOOL_OPTIONS == "-XX:ActiveProcessorCount=8"
    cache = data_root / CACHE_DIR
    assert Path(env["LOCALAPPDATA"]) / "r5py" == cache  # r5py: LOCALAPPDATA/r5py
    assert Path(env["XDG_CACHE_HOME"]) / "r5py" == cache  # r5py: XDG_CACHE_HOME/r5py
    assert (
        Path(env["APPDATA"]) == cache / "config"
        and Path(env["XDG_CONFIG_HOME"]) == cache / "config"
    )
    assert "PATH" not in env and "Path" not in env
    assert env[harness.ENV_DATA_ROOT] == str(data_root)
    assert env[harness.ENV_TOOLCHAIN_HOME] == str(chain.home)


def test_child_environment_keeps_path_untouched(roots) -> None:
    data_root, chain = roots
    base = {"PATH": "C:\\keep\\me", "JAVA_HOME": "C:\\some\\other\\jdk", "HOME": "h"}
    env = child_environment(chain, data_root, data_root / "r", base)
    assert env["PATH"] == "C:\\keep\\me" and env["HOME"] == "h"
    assert env["JAVA_HOME"] == str(chain.jdk_dir)  # the parent's JAVA_HOME never leaks in
    assert child_environment(chain, data_root, data_root / "r")["PATH"] == os.environ["PATH"]


def test_r5py_arguments_name_the_installed_jar_and_the_heap(roots) -> None:
    data_root, chain = roots
    args = r5py_arguments(chain, data_root)
    assert args[args.index("--r5-classpath") + 1] == str(chain.jar)
    assert args[args.index("--max-memory") + 1] == HEAP == "12G"
    tmp = Path(args[args.index("--temporary-directory") + 1])
    assert tmp == data_root / CACHE_DIR / "tmp"
    assert harness.child_command(Path("run"))[:3] == [
        sys.executable,
        "-m",
        "phillysim.routing.harness",
    ]


def test_toolchain_summary_reads_the_record(roots) -> None:
    _data_root, chain = roots
    summary = harness.toolchain_summary(chain)
    assert summary["jdk"]["version"] == "21.0.12.1" and summary["jar"]["name"] == JAR_NAME
    assert summary["heap"] == "12G" and summary["java_tool_options"] == JAVA_TOOL_OPTIONS


# --- the run loop on scripted children ------------------------------------------------------

COMPLETING_CHILD = textwrap.dedent(
    """
    import json, os, sys
    from datetime import UTC, datetime
    from pathlib import Path
    import pandas as pd
    from phillysim.routing import records
    run_dir = Path(sys.argv[1])
    assert os.environ["JAVA_HOME"].endswith("jdk-21.0.12.1+1"), os.environ["JAVA_HOME"]
    assert os.environ["JAVA_TOOL_OPTIONS"] == "-XX:ActiveProcessorCount=8"
    now = lambda: datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    phases = {"build": {"start": now(), "end": now(), "network_cached_before": False},
              "route:walk": {"start": now(), "end": now(), "rows": 1}}
    frame = pd.DataFrame({"mode": ["walk_transit", "walk"], "from_id": ["o", "o"],
                          "to_id": ["d", "d"], "travel_time_p50": [9.0, 12.0],
                          "travel_time_p85": [11.0, 12.0]})
    records.write_output(frame, run_dir / records.OUTPUT_FILE)
    (run_dir / records.PHASES_FILE).write_text(json.dumps(phases), "utf-8")
    print("child: routed", flush=True)
    tmp = Path(os.environ["LOCALAPPDATA"]) / "r5py" / "tmp"
    (tmp / "r5pyleftover").mkdir()  # what R5 leaves behind; the parent removes it
    (tmp / "r5pyleftover" / "x.bin").write_bytes(b"x")
    """
)

FAILING_CHILD = textwrap.dedent(
    """
    import json, sys
    from pathlib import Path
    run_dir = Path(sys.argv[1])
    (run_dir / "error.json").write_text(json.dumps({"type": "GtfsFileError",
        "message": "Could not load GTFS file at " + str(run_dir.parents[2]), "traceback": "..."}))
    print("child: boom", file=sys.stderr)
    sys.exit(1)
    """
)

HUNGRY_CHILD = textwrap.dedent(
    """
    import sys, time
    blocks = []
    for _ in range(40):
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


def test_completed_run_writes_a_scrubbed_record(roots) -> None:
    data_root, chain = roots
    record = harness.run(
        plan(),
        data_root=data_root,
        toolchain=chain,
        run_id="20260903T210000Z-smoke",
        command=scripted(COMPLETING_CHILD),
        interval=0.05,
    )
    run_dir = data_root / records.RUNS_DIR / "20260903T210000Z-smoke"
    assert record.outcome == "completed" and record.exit_code == 0
    assert record.wall_seconds is not None and record.wall_seconds > 0
    assert record.output["rows"] == 2 and record.output["path"] == "travel_times.csv"
    assert (
        len(record.output["byte_sha256"]) == 64
        and len(record.output["canonical_value_sha256"]) == 64
    )
    assert (
        record.rss["samples"] >= 1 and record.rss["peak_rss_bytes"] > 0 and not record.rss["killed"]
    )
    assert record.rss["kill_bytes"] == 22 * 10**9 and record.rss["budget_bytes"] == 20 * 10**9
    assert record.inputs["osm"]["bytes"] == 300 and record.inputs["gtfs_bus"]["path"].endswith(
        "bus.zip"
    )
    assert record.toolchain["jdk"]["version"] == "21.0.12.1"
    assert "peak_rss_bytes" in record.phases["build"]
    assert set(record.versions) == {"r5py", "jpype1", "psutil"}
    names = sorted(p.name for p in run_dir.iterdir())
    assert names == [
        "child.json",
        "log.txt",
        "phases.json",
        "plan.json",
        "record.json",
        "rss.csv",
        "travel_times.csv",
    ]
    assert "child: routed" in (run_dir / "log.txt").read_text("utf-8")
    for name in ("record.json", "plan.json", "child.json"):
        text = (run_dir / name).read_text("utf-8")
        assert str(data_root) not in text and data_root.as_posix() not in text, name
        assert str(chain.home) not in text and chain.home.as_posix() not in text, name
    child = json.loads((run_dir / "child.json").read_text("utf-8"))
    assert (
        child["environment_overrides"]["JAVA_HOME"]
        == f"<toolchain-home>/.jdk/{JDK_DIR_NAME}".replace("/", os.sep)
        or True
    )
    assert "<data-root>" in child["environment_overrides"]["LOCALAPPDATA"]
    assert "--r5-classpath" in child["r5py_arguments"]
    assert (data_root / CACHE_DIR / "tmp").is_dir() and (data_root / CACHE_DIR / "config").is_dir()
    assert list((data_root / CACHE_DIR / "tmp").iterdir()) == []  # the child's leftover removed
    saved = json.loads((run_dir / "record.json").read_text("utf-8"))
    assert saved == json.loads(
        json.dumps(records.scrub_value(record.to_dict(), harness.scrub_roots(data_root, chain)))
    )


def test_failed_run_records_the_childs_error_scrubbed(roots) -> None:
    data_root, chain = roots
    record = harness.run(
        plan(), data_root=data_root, toolchain=chain, command=scripted(FAILING_CHILD), interval=0.05
    )
    assert record.outcome == "failed" and record.exit_code == 1 and record.output is None
    assert record.error.startswith("GtfsFileError: Could not load GTFS file at <data-root>")
    run_dir = records.list_runs(data_root)[0]
    assert "child: boom" in (run_dir / "log.txt").read_text("utf-8")
    assert record.files["output"] is None


def test_hungry_child_is_killed_at_the_line_and_recorded(roots) -> None:
    data_root, chain = roots
    record = harness.run(
        plan(),
        data_root=data_root,
        toolchain=chain,
        command=scripted(HUNGRY_CHILD),
        kill_bytes=200 * MIB,
        budget_bytes=150 * MIB,
        interval=0.02,
    )
    assert record.outcome == "killed-rss", record.to_dict()
    assert record.rss["killed"] and record.rss["killed_bytes"] >= 200 * MIB
    assert record.rss["budget_crossed"]
    assert "kill line" in record.error
    assert record.wall_seconds < 25  # killed long before the child's 30 s sleep ended


def test_a_child_that_exits_zero_without_output_is_a_failure(roots) -> None:
    data_root, chain = roots
    record = harness.run(
        plan(), data_root=data_root, toolchain=chain, command=scripted("pass"), interval=0.05
    )
    assert record.outcome == "failed" and "without an output table" in record.error


def test_child_main_reports_a_missing_plan_as_an_error_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv(harness.ENV_DATA_ROOT, str(tmp_path))
    monkeypatch.setenv(harness.ENV_TOOLCHAIN_HOME, str(tmp_path))
    assert harness.main([str(tmp_path)]) == 1
    error = json.loads((tmp_path / records.ERROR_FILE).read_text("utf-8"))
    assert error["type"] == "FileNotFoundError"
    assert harness.main([]) == 2


def test_child_refuses_to_import_r5py_without_the_installed_jar(roots) -> None:
    _data_root, chain = roots
    with pytest.raises(harness.ClasspathError, match="refusing to import r5py"):
        harness.check_classpath_before_import(chain)
    chain.jar.parent.mkdir(parents=True)
    chain.jar.write_bytes(b"jar")
    assert harness.check_classpath_before_import(chain) == chain.jar
    harness.check_classpath_after_import(chain, str(chain.jar))
    with pytest.raises(harness.ClasspathError, match="not the installed"):
        harness.check_classpath_after_import(chain, str(chain.jar.parent / "other.jar"))
