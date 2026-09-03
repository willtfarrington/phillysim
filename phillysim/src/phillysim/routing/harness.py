"""The routing subprocess and its environment (EP-13; ADR-0008).

Every JVM run happens in a **child process**, never in the CLI process, with an
environment built per invocation:

* ``JAVA_HOME`` = the project-local JDK (:mod:`phillysim.routing.toolchain`);
  ``PATH`` is untouched;
* ``JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=8`` (architecture.md's
  parallelism cap; R5 sizes its thread pool from the processor count);
* r5py's own arguments, read by its ``configargparse`` parser from the child's
  ``sys.argv``: ``--max-memory 12G`` (the heap), ``--r5-classpath`` naming the
  installed jar (so r5py's own download path is never exercised), and
  ``--temporary-directory`` under the data root;
* r5py's cache directory under the data root: r5py resolves it from
  ``LOCALAPPDATA`` (Windows) or ``XDG_CACHE_HOME`` (Linux) plus ``r5py``, so
  the child's environment points both at ``<data root>/cache``; it writes the
  built network there (``<digest>.mapdb``, ``<digest>.transport_network``),
  copies its inputs there as working copies (so nothing is written beside a
  raw or intermediate file), and expires cache files older than two weeks;
  ``APPDATA`` / ``XDG_CONFIG_HOME`` are pointed under the same directory so
  the ``r5py.yml`` template r5py writes on first import lands there and no
  user-level configuration file is read.

The parent (:func:`run`) writes the plan, starts the child with its stdout and
stderr on ``log.txt``, samples the process tree (:mod:`~phillysim.routing.sampler`),
waits, and writes the record. The child (:func:`main`, ``python -m
phillysim.routing.harness <run dir>``) is the only code that imports r5py, and
only inside the function that runs there.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psutil

from phillysim.config import find_repo_root
from phillysim.routing import records
from phillysim.routing.records import (
    CANCELLED,
    CHILD_FILE,
    COMPLETED,
    ERROR_FILE,
    FAILED,
    KILLED_RSS,
    LOG_FILE,
    OUTPUT_FILE,
    PHASES_FILE,
    PLAN_FILE,
    RECORD_FILE,
    RSS_FILE,
    RunPlan,
    RunRecord,
)
from phillysim.routing.sampler import (
    BUDGET_BYTES,
    DEFAULT_INTERVAL,
    KILL_BYTES,
    Sampler,
    write_rss_csv,
)
from phillysim.routing.toolchain import PYTHON_PACKAGES, Toolchain, package_version, read_record

HEAP = "12G"  # methodology.md / ADR-0008: the 12 GB heap
PROCESSOR_COUNT = 8  # architecture.md: <= 8 of 16 logical processors
JAVA_TOOL_OPTIONS = f"-XX:ActiveProcessorCount={PROCESSOR_COUNT}"
CACHE_DIR = "cache/r5py"
ENV_DATA_ROOT = "PHILLYSIM_ROUTING_DATA_ROOT"
ENV_TOOLCHAIN_HOME = "PHILLYSIM_ROUTING_TOOLCHAIN_HOME"
ENV_RUN_DIR = "PHILLYSIM_ROUTING_RUN_DIR"
#: r5py's TransportMode names per plan mode (walk+transit: transit with walk access/egress).
R5_MODES: Mapping[str, tuple[str, ...]] = {"walk": ("WALK",), "walk_transit": ("TRANSIT", "WALK")}


def cache_dir(data_root: Path) -> Path:
    return data_root / CACHE_DIR


def r5py_arguments(toolchain: Toolchain, data_root: Path) -> list[str]:
    """The arguments r5py's parser reads from the child's ``sys.argv``."""
    return [
        "--max-memory",
        HEAP,
        "--r5-classpath",
        str(toolchain.jar),
        "--temporary-directory",
        str(cache_dir(data_root) / "tmp"),
    ]


def environment_overrides(toolchain: Toolchain, data_root: Path, run_dir: Path) -> dict[str, str]:
    """The variables the child gets on top of the parent's environment (``PATH`` untouched)."""
    cache = cache_dir(data_root)
    return {
        "JAVA_HOME": str(toolchain.jdk_dir),
        "JAVA_TOOL_OPTIONS": JAVA_TOOL_OPTIONS,
        "LOCALAPPDATA": str(cache.parent),  # r5py: LOCALAPPDATA/r5py on Windows
        "XDG_CACHE_HOME": str(cache.parent),  # r5py: XDG_CACHE_HOME/r5py on Linux
        "APPDATA": str(cache / "config"),  # r5py: APPDATA/r5py.yml (its template) on Windows
        "XDG_CONFIG_HOME": str(cache / "config"),  # the same on Linux
        "PYTHONUTF8": "1",
        ENV_DATA_ROOT: str(data_root),
        ENV_TOOLCHAIN_HOME: str(toolchain.home),
        ENV_RUN_DIR: str(run_dir),
    }


def child_environment(
    toolchain: Toolchain, data_root: Path, run_dir: Path, base: Mapping[str, str] | None = None
) -> dict[str, str]:
    env = dict(os.environ if base is None else base)
    env.update(environment_overrides(toolchain, data_root, run_dir))
    return env


def child_command(run_dir: Path) -> list[str]:
    return [sys.executable, "-m", "phillysim.routing.harness", str(run_dir)]


def scrub_roots(data_root: Path, toolchain: Toolchain) -> dict[str, Path]:
    roots = {"<data-root>": data_root, "<toolchain-home>": toolchain.home}
    repo = find_repo_root(toolchain.home) or find_repo_root(data_root)
    if repo is not None:
        roots["<repo-root>"] = repo
    return roots


def _utc(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).isoformat(timespec="seconds").replace("+00:00", "Z")


def toolchain_summary(toolchain: Toolchain) -> dict[str, Any]:
    """What the record says about the toolchain: the recorded digests and versions."""
    record = read_record(toolchain) or {}
    return {
        "jdk": {
            k: record.get("jdk", {}).get(k)
            for k in ("release", "version", "sha256", "java_version")
        },
        "jar": {k: record.get("jar", {}).get(k) for k in ("release", "name", "sha256")},
        "heap": HEAP,
        "java_tool_options": JAVA_TOOL_OPTIONS,
    }


def run(
    plan: RunPlan,
    *,
    data_root: Path,
    toolchain: Toolchain,
    run_id: str | None = None,
    run_dir: Path | None = None,
    command: Callable[[Path], list[str]] = child_command,
    kill_bytes: int = KILL_BYTES,
    budget_bytes: int = BUDGET_BYTES,
    interval: float = DEFAULT_INTERVAL,
    echo: Callable[[str], None] | None = None,
) -> RunRecord:
    """Run ``plan`` in a child under the sampler; write the run directory; return the record.

    ``command`` builds the child's argv from the run directory (the tests substitute a
    scripted child). ``run_dir`` overrides the default ``<data root>/runs/routing/<run id>``
    (the matrix driver, EP-14, keeps a night's runs under one directory). Ctrl-C kills the
    tree and records ``cancelled``.
    """
    say = echo or (lambda _line: None)
    run_id = run_id or records.run_id(plan.slug)
    run_dir = run_dir if run_dir is not None else records.run_dir(data_root, run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    roots = scrub_roots(data_root, toolchain)
    cache_dir(data_root).mkdir(parents=True, exist_ok=True)
    (cache_dir(data_root) / "tmp").mkdir(exist_ok=True)
    (cache_dir(data_root) / "config").mkdir(exist_ok=True)
    records.write_json(run_dir / PLAN_FILE, plan.to_dict(), roots)
    argv = command(run_dir)
    env = child_environment(toolchain, data_root, run_dir)
    records.write_json(
        run_dir / CHILD_FILE,
        {
            "command": argv,
            "environment_overrides": environment_overrides(toolchain, data_root, run_dir),
            "r5py_arguments": r5py_arguments(toolchain, data_root),
        },
        roots,
    )
    tmp_dir = cache_dir(data_root) / "tmp"
    tmp_before = {p.name for p in tmp_dir.iterdir()}
    started_at = datetime.now(UTC)
    started = time.perf_counter()
    say(f"run {run_id}: starting the routing child (kill at {kill_bytes / 10**9:.0f} GB RSS)")
    outcome, exit_code, error = FAILED, None, None
    with (run_dir / LOG_FILE).open("wb") as log:
        process = subprocess.Popen(
            argv, env=env, stdout=log, stderr=subprocess.STDOUT, cwd=str(run_dir)
        )
        sampler = Sampler.for_process(
            psutil.Process(process.pid),
            kill_bytes=kill_bytes,
            budget_bytes=budget_bytes,
            interval=interval,
        )
        sampler.start()
        try:
            exit_code = process.wait()
        except KeyboardInterrupt:
            from phillysim.routing.sampler import kill_tree

            kill_tree(psutil.Process(process.pid))
            exit_code = process.wait()
            outcome = CANCELLED
        finally:
            sampler.stop()
            sampler.join(timeout=10)
    wall = time.perf_counter() - started
    finished_at = datetime.now(UTC)
    result = sampler.result
    # R5 leaves its temporary directory behind when the JVM is killed or fails (its shutdown
    # hook never runs); remove what this run created so the cache does not grow run by run.
    for leftover in sorted(tmp_dir.iterdir()):
        if leftover.name not in tmp_before:
            shutil.rmtree(leftover, ignore_errors=True)
    write_rss_csv(run_dir / RSS_FILE, result.samples)
    phases = records.read_json(run_dir / PHASES_FILE) if (run_dir / PHASES_FILE).exists() else {}
    for phase in phases.values():
        if isinstance(phase, dict):
            phase["peak_rss_bytes"] = result.peak_between(phase.get("start"), phase.get("end"))
    output: dict[str, Any] | None = None
    output_path = run_dir / OUTPUT_FILE
    if result.killed:
        outcome = KILLED_RSS
        error = f"process tree reached {result.killed_bytes} bytes RSS (kill line {kill_bytes})"
    elif outcome == CANCELLED:
        error = "cancelled by the operator"
    elif exit_code == 0 and output_path.is_file():
        outcome = COMPLETED
        frame = records.read_output(output_path)
        output = {
            "path": OUTPUT_FILE,
            "rows": int(len(frame)),
            "bytes": output_path.stat().st_size,
            "byte_sha256": records.sha256_file(output_path),
            "canonical_value_sha256": records.canonical_value_digest(frame),
        }
    else:
        outcome = FAILED
        if (run_dir / ERROR_FILE).exists():
            err = records.read_json(run_dir / ERROR_FILE)
            error = f"{err.get('type')}: {err.get('message')}"
        else:
            error = f"the child exited {exit_code} without an output table (see {LOG_FILE})"
    record = RunRecord(
        run_id=run_id,
        slug=plan.slug,
        outcome=outcome,
        started_at=_utc(started_at),
        finished_at=_utc(finished_at),
        wall_seconds=round(wall, 3),
        exit_code=exit_code,
        phases=phases,
        rss=result.to_dict(),
        toolchain=toolchain_summary(toolchain),
        versions={name: package_version(name) for name in PYTHON_PACKAGES},
        inputs=records.input_digests(data_root, plan.inputs),
        output=output,
        error=records.scrub(error, roots) if error else None,
        files={
            "plan": PLAN_FILE,
            "record": RECORD_FILE,
            "rss": RSS_FILE,
            "log": LOG_FILE,
            "child": CHILD_FILE,
            "output": OUTPUT_FILE if output else None,
        },
    )
    records.write_json(run_dir / RECORD_FILE, record.to_dict(), roots)
    say(
        f"run {run_id}: {outcome}; wall {wall:.1f} s; peak RSS {result.peak_bytes / 10**9:.2f} GB "
        f"at {result.peak_elapsed_s} s; {len(result.samples)} samples"
    )
    return record


# --- the child -----------------------------------------------------------------------------


def _phase(phases: dict[str, Any], name: str, key: str) -> None:
    phases.setdefault(name, {})[key] = _utc()


def route(plan: RunPlan, data_root: Path, run_dir: Path, toolchain: Toolchain) -> None:
    """The child's body: configure r5py through ``sys.argv``, build the network, route each
    mode, write the output table and the phase timings. r5py is imported here and nowhere
    else."""
    phases: dict[str, Any] = {}
    sys.argv = ["r5py", *r5py_arguments(toolchain, data_root)]
    try:
        _route(plan, data_root, run_dir, phases, toolchain)
    finally:
        # The phase timings are evidence even when a later phase fails.
        (run_dir / PHASES_FILE).write_text(
            json.dumps(phases, indent=2, sort_keys=True) + "\n", "utf-8"
        )


class ClasspathError(RuntimeError):
    """The jar r5py would run is not the installed one."""


def check_classpath_before_import(toolchain: Toolchain) -> Path:
    """Refuse to import r5py unless the installed jar exists: r5py falls back to its own
    download (into its cache directory) when ``--r5-classpath`` names a missing file."""
    if not toolchain.jar.is_file():
        raise ClasspathError(
            f"the installed jar is missing ({toolchain.jar.name}); refusing to import r5py, "
            "which would download its own jar instead (run `phillysim toolchain install`)"
        )
    return toolchain.jar


def check_classpath_after_import(toolchain: Toolchain, r5_classpath: str) -> None:
    """The classpath r5py resolved must be the installed jar, byte for byte the same path."""
    if Path(r5_classpath).resolve() != toolchain.jar.resolve():
        raise ClasspathError(
            f"r5py resolved its classpath to {Path(r5_classpath).name!r}, not the installed "
            f"{toolchain.jar.name!r}; refusing to route"
        )


def _route(
    plan: RunPlan, data_root: Path, run_dir: Path, phases: dict[str, Any], toolchain: Toolchain
) -> None:
    check_classpath_before_import(toolchain)
    _phase(phases, "import", "start")
    import geopandas as gpd  # noqa: PLC0415 - the child's own imports
    import pandas as pd
    import r5py
    from r5py.util.classpath import R5_CLASSPATH
    from r5py.util.config import Config

    _phase(phases, "import", "end")
    check_classpath_after_import(toolchain, R5_CLASSPATH)
    phases["import"]["r5_classpath"] = Path(R5_CLASSPATH).name
    cache = Path(Config().CACHE_DIR)
    before = {p.name for p in cache.glob("*.transport_network")}
    osm = data_root / plan.inputs["osm"]
    gtfs = [
        data_root / rel for label, rel in sorted(plan.inputs.items()) if label.startswith("gtfs")
    ]
    _phase(phases, "build", "start")
    network = r5py.TransportNetwork(osm, gtfs)
    _phase(phases, "build", "end")
    after = {p.name for p in cache.glob("*.transport_network")}
    phases["build"]["network_cached_before"] = bool(before & after) and before == after
    phases["build"]["cache_files"] = sorted(after)

    def frame(points):
        return gpd.GeoDataFrame(
            {"id": [p.id for p in points]},
            geometry=gpd.points_from_xy([p.lon for p in points], [p.lat for p in points]),
            crs="EPSG:4326",
        )

    origins, destinations = frame(plan.origins), frame(plan.destinations)
    departure = datetime.strptime(plan.departure, "%Y-%m-%dT%H:%M")
    tables = []
    for mode in plan.modes:
        _phase(phases, f"route:{mode}", "start")
        matrix = r5py.TravelTimeMatrix(
            network,
            origins=origins,
            destinations=destinations,
            transport_modes=[r5py.TransportMode[m] for m in R5_MODES[mode]],
            departure=departure,
            departure_time_window=timedelta(minutes=plan.window_minutes),
            percentiles=list(plan.percentiles),
            speed_walking=plan.speed_walking_kmh,
            max_time=timedelta(minutes=plan.max_time_minutes),
            snap_to_network=plan.snap_to_network,
        )
        table = pd.DataFrame(matrix.drop(columns=[c for c in ("geometry",) if c in matrix.columns]))
        table.insert(0, "mode", mode)
        tables.append(table)
        _phase(phases, f"route:{mode}", "end")
        phases[f"route:{mode}"]["rows"] = int(len(table))
    output = pd.concat(tables, ignore_index=True)
    records.write_output(output, run_dir / OUTPUT_FILE)


def main(argv: list[str] | None = None) -> int:
    """``python -m phillysim.routing.harness <run dir>``: the child's entry point."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m phillysim.routing.harness <run dir>", file=sys.stderr)
        return 2
    run_dir = Path(args[0])
    try:
        data_root = Path(os.environ[ENV_DATA_ROOT])
        toolchain = Toolchain(Path(os.environ[ENV_TOOLCHAIN_HOME]))
        plan = RunPlan.from_dict(records.read_json(run_dir / PLAN_FILE))
        route(plan, data_root, run_dir, toolchain)
    except BaseException as exc:  # noqa: BLE001 - the child reports everything to the parent
        (run_dir / ERROR_FILE).write_text(
            json.dumps(
                {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
                indent=2,
            )
            + "\n",
            "utf-8",
        )
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - the child process
    sys.exit(main())
