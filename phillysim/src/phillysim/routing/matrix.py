"""The matrix driver: a plan's runs executed one by one, resumable, under the harness (EP-14).

``phillysim route matrix --plan FILE`` runs a :mod:`~phillysim.routing.plan` in
order, one run per child process under EP-13's sampler, and keeps a **night**
directory ``<data root>/runs/routing/<night-id>/`` with:

* ``night.json``: the night record (the plan's name and digest, the points'
  digest, the feeds' windows, the run order, per-run status / wall / peak RSS /
  output digests / sanity counts, the core wall against the plan's limit, the
  peak RSS over the night, the state and the outcome code; the driver's
  invocations, interruptions, and, for a rehearsal subset, the extrapolated
  wall of the full night);
* ``points.parquet``: every origin and destination the night routes, built once;
* ``driver.log``: the driver's own lines, appended across invocations;
* one harness run directory per run, ``<run name>/`` (EP-13's files plus
  ``travel_times.parquet``, the matrix in the data dictionary's shape, and
  ``matrix.json``, its digests and sanity counts); an earlier attempt that did
  not complete is kept as ``<run name>.attempt<N>/``.

**Resume:** on re-invocation a run already ``completed`` in the night directory
is skipped; a run that failed, was cancelled, or was interrupted (the driver
died mid-run: its status still reads ``running``) is run again, the attempt
kept. **Kill:** ``killed-rss`` on a core run, or the core runs' walls together
over the plan's limit, sets the outcome code ``KILLED-BY-EVIDENCE`` and stops
the night unless ``--continue-after-kill`` was given (the evidence is the run,
not the recovery); a killed non-core run is recorded and the night goes on. A
``failed`` or ``cancelled`` run stops the night in state ``stopped`` (re-invoke
to resume). **States:** ``running`` (a driver is executing), ``stopped``,
``finished`` (every run done, no kill), ``KILLED-BY-EVIDENCE``.

The driver never imports r5py: it launches the harness child per run and reads
the records back.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import psutil

from phillysim.routing import harness, records
from phillysim.routing.plan import (
    POINTS_FILE,
    ROLE_DESTINATION,
    ROLE_ORIGIN,
    MatrixPlan,
    MatrixRun,
    PlanError,
    build_points,
    check_feed_windows,
    describe,
    feed_windows,
    read_points,
    run_plan,
    write_points,
)
from phillysim.routing.records import COMPLETED, KILLED_RSS, RunRecord
from phillysim.routing.toolchain import Toolchain

NIGHT_FILE = "night.json"
DRIVER_LOG = "driver.log"
#: A detached launch's redirected streams (``launch.log``, ``launch.err``) may pre-exist.
LAUNCH_PREFIX = "launch."
MATRIX_FILE = "travel_times.parquet"
MATRIX_INFO_FILE = "matrix.json"
NIGHT_SCHEMA_VERSION = 1
#: The data dictionary's travel-time matrix key.
MATRIX_KEY: tuple[str, ...] = ("origin_geoid", "site_id", "mode")
MATRIX_COLUMNS: tuple[str, ...] = (*MATRIX_KEY, "time_median_min", "time_p85_min")
#: methodology.md "Validation": the share of finite pairs a core run must reach.
FINITE_SHARE_GATE = 0.95

RUNNING, STOPPED, FINISHED, KILLED_BY_EVIDENCE = (
    "running",
    "stopped",
    "finished",
    "KILLED-BY-EVIDENCE",
)
STATES: tuple[str, ...] = (RUNNING, STOPPED, FINISHED, KILLED_BY_EVIDENCE)
PENDING = "pending"

Runner = Callable[..., RunRecord]


def _utc(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).isoformat(timespec="seconds").replace("+00:00", "Z")


def night_id(
    plan: MatrixPlan, origins_subset: int | None = None, now: datetime | None = None
) -> str:
    suffix = f"-subset{origins_subset}" if origins_subset else ""
    return f"{records.utc_stamp(now)}-{plan.name}{suffix}"


def night_dir(data_root: Path, night_id_: str) -> Path:
    return data_root / records.RUNS_DIR / night_id_


def list_nights(data_root: Path) -> list[Path]:
    return [p for p in records.list_runs(data_root) if (p / NIGHT_FILE).is_file()]


# --- the matrix in the dictionary's shape, and the sanity counts ------------------------------


def matrix_from_output(
    raw: pd.DataFrame, origins: Sequence[str], destinations: Sequence[str], mode: str, max_time: int
) -> pd.DataFrame:
    """The full origin × destination grid for ``mode`` in the data dictionary's shape,
    censored at ``max_time``: a pair R5 found no route for within ``max_time`` (missing
    value) or dropped (an unsnapped point) takes the censor value; nothing exceeds it."""
    grid = pd.MultiIndex.from_product(
        [list(origins), list(destinations)], names=["origin_geoid", "site_id"]
    ).to_frame(index=False)
    part = raw[raw["mode"] == mode][["from_id", "to_id", "travel_time_p50", "travel_time_p85"]]
    part = part.rename(
        columns={
            "from_id": "origin_geoid",
            "to_id": "site_id",
            "travel_time_p50": "time_median_min",
            "travel_time_p85": "time_p85_min",
        }
    )
    part["origin_geoid"] = part["origin_geoid"].astype(str)
    part["site_id"] = part["site_id"].astype(str)
    if part.duplicated(["origin_geoid", "site_id"]).any():
        raise ValueError("the output table repeats an origin-destination pair")
    frame = grid.merge(part, on=["origin_geoid", "site_id"], how="left")
    frame.insert(2, "mode", mode)
    for column in ("time_median_min", "time_p85_min"):
        frame[column] = frame[column].astype("float64").fillna(max_time).clip(upper=max_time)
    frame = frame.sort_values(list(MATRIX_KEY), kind="stable").reset_index(drop=True)
    return frame[list(MATRIX_COLUMNS)]


def _summary(values: pd.Series) -> dict[str, float | None]:
    finite = values.dropna()
    if finite.empty:
        return {k: None for k in ("min", "p10", "p25", "p50", "p75", "p90", "max", "mean")}
    q = finite.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    return {
        "min": float(finite.min()),
        "p10": float(q[0.1]),
        "p25": float(q[0.25]),
        "p50": float(q[0.5]),
        "p75": float(q[0.75]),
        "p90": float(q[0.9]),
        "max": float(finite.max()),
        "mean": round(float(finite.mean()), 2),
    }


def sanity_counts(
    raw: pd.DataFrame, origins: Sequence[str], destinations: Sequence[str], mode: str, max_time: int
) -> dict[str, Any]:
    """Computed on the child's raw output: the share of finite pairs (a typical time under
    the censor; methodology.md's ≥ 95 % gate), the pairs at the censor (no route within
    ``max_time``, or dropped), and a distribution summary of the finite times."""
    expected = len(origins) * len(destinations)
    part = raw[raw["mode"] == mode]
    p50 = pd.to_numeric(part["travel_time_p50"], errors="coerce")
    p85 = pd.to_numeric(part["travel_time_p85"], errors="coerce")
    finite_mask = p50 < max_time
    finite = int(finite_mask.sum())
    finite_p85 = int((p85 < max_time).sum())
    per_origin = part.assign(finite=finite_mask).groupby("from_id")["finite"].sum()
    origins_without = sorted(set(origins) - set(per_origin[per_origin > 0].index.astype(str)))
    return {
        "pairs_expected": expected,
        "rows": int(len(part)),
        "missing_rows": expected - int(len(part)),
        "unreachable": int(p50.isna().sum()),
        "finite_pairs": finite,
        "finite_share": round(finite / expected, 6) if expected else None,
        "finite_share_gate": FINITE_SHARE_GATE,
        "finite_share_gate_met": bool(expected and finite / expected >= FINITE_SHARE_GATE),
        "at_censor": expected - finite,
        "finite_pairs_p85": finite_p85,
        "origins_without_a_finite_pair": len(origins_without),
        "origins_without_a_finite_pair_ids": origins_without[:20],
        "median_minutes": _summary(p50[finite_mask]),
        "p85_minutes": _summary(p85[finite_mask]),
        "p85_minus_median_mean": (
            round(float((p85[finite_mask] - p50[finite_mask]).mean()), 2) if finite else None
        ),
    }


def write_matrix(frame: pd.DataFrame, path: Path) -> dict[str, Any]:
    """Write the matrix as Parquet (sorted by key) and return its digests."""
    frame.to_parquet(path, index=False)
    return {
        "path": path.name,
        "rows": int(len(frame)),
        "bytes": path.stat().st_size,
        "byte_sha256": records.sha256_file(path),
        "canonical_value_sha256": records.canonical_value_digest(frame, MATRIX_KEY),
        "key": list(MATRIX_KEY),
        "columns": list(MATRIX_COLUMNS),
    }


def finish_run_output(
    run_dir: Path, points: pd.DataFrame, run: MatrixRun, max_time: int
) -> dict[str, Any]:
    """After a completed run: the matrix Parquet, its digests, the sanity counts, and
    ``matrix.json`` in the run directory."""
    raw = records.read_output(run_dir / records.OUTPUT_FILE)
    origins = [str(i) for i in points.loc[points["role"] == ROLE_ORIGIN, "id"]]
    destinations = [str(i) for i in points.loc[points["role"] == ROLE_DESTINATION, "id"]]
    frame = matrix_from_output(raw, origins, destinations, run.mode, max_time)
    info = {
        "matrix": write_matrix(frame, run_dir / MATRIX_FILE),
        "sanity": sanity_counts(raw, origins, destinations, run.mode, max_time),
        "mode": run.mode,
        "speed_walking_kmh": run.speed_walking_kmh,
        "departure": run.departure,
        "window_minutes": run.window_minutes,
        "departures": run.departures,
        "max_time_minutes": max_time,
    }
    records.write_json(run_dir / MATRIX_INFO_FILE, info, {})
    return info


# --- the night record ---------------------------------------------------------------------


class Night:
    """``night.json`` and the directory around it."""

    def __init__(self, directory: Path, data: dict[str, Any], roots: Mapping[str, Path]):
        self.dir = directory
        self.data = data
        self.roots = roots

    @property
    def path(self) -> Path:
        return self.dir / NIGHT_FILE

    @property
    def id(self) -> str:
        return self.data["night_id"]

    @property
    def state(self) -> str:
        return self.data["state"]

    @property
    def runs(self) -> dict[str, dict[str, Any]]:
        return self.data["runs"]

    def save(self) -> None:
        self.data["updated_at"] = _utc()
        records.write_json(self.path, self.data, self.roots)

    @classmethod
    def load(cls, directory: Path, roots: Mapping[str, Path] | None = None) -> Night:
        return cls(directory, records.read_json(directory / NIGHT_FILE), roots or {})

    @classmethod
    def create(
        cls,
        directory: Path,
        plan: MatrixPlan,
        *,
        origins_subset: int | None,
        points: pd.DataFrame,
        inputs: Mapping[str, str],
        windows: Mapping[str, Mapping[str, str | None]],
        continue_after_kill: bool,
        roots: Mapping[str, Path],
        now: datetime | None = None,
    ) -> Night:
        directory.mkdir(parents=True, exist_ok=True)
        # A detached launch redirects its standard streams into the night directory before
        # the driver starts (the README's launch step): those files are allowed, nothing else.
        stray = [p.name for p in directory.iterdir() if not p.name.startswith(LAUNCH_PREFIX)]
        if stray:
            raise PlanError(
                f"night directory {directory.name} is not empty ({', '.join(sorted(stray))}) "
                f"and has no {NIGHT_FILE}"
            )
        write_points(points, directory / POINTS_FILE)
        n_origins = int((points["role"] == ROLE_ORIGIN).sum())
        n_destinations = int((points["role"] == ROLE_DESTINATION).sum())
        data = {
            "schema_version": NIGHT_SCHEMA_VERSION,
            "night_id": directory.name,
            "plan": {
                "name": plan.name,
                "file": plan.source,
                "sha256": plan.sha256,
                "title": plan.title,
                "runs": list(plan.run_names),
                "core_runs": list(plan.core_runs),
                "core_wall_limit_hours": plan.core_wall_limit_hours,
                "time_zone": plan.time_zone,
                "percentiles": list(plan.percentiles),
                "max_time_minutes": plan.max_time_minutes,
                "snap_to_network": plan.snap_to_network,
            },
            "origins": {
                "count": n_origins,
                "full_count": plan.origins.count,
                "subset": origins_subset,
                "description": plan.origins.description,
                "table": plan.origins.path,
            },
            "destinations": {
                "count": n_destinations,
                "description": plan.destinations.description,
                "table": plan.destinations.path,
            },
            "points": {
                "file": POINTS_FILE,
                "sha256": records.sha256_file(directory / POINTS_FILE),
                "rows": int(len(points)),
            },
            "inputs": dict(inputs),
            "feeds": {k: dict(v) for k, v in windows.items()},
            "state": RUNNING,
            "outcome_code": None,
            "kill_reason": None,
            "stop_reason": None,
            "continue_after_kill": continue_after_kill,
            "started_at": _utc(now),
            "updated_at": None,
            "finished_at": None,
            "driver": {"pid": None, "create_time": None, "invocations": []},
            "interruptions": [],
            "runs": {
                r.name: {
                    "order": i + 1,
                    "role": r.role,
                    "repeat_of": r.repeat_of,
                    "core": plan.is_core(r.name),
                    "mode": r.mode,
                    "speed_walking_kmh": r.speed_walking_kmh,
                    "departure": r.departure,
                    "window_minutes": r.window_minutes,
                    "departures": r.departures,
                    "status": PENDING,
                    "attempts": 0,
                    "dir": r.name,
                }
                for i, r in enumerate(plan.runs)
            },
            "core_wall_seconds": None,
            "core_wall_limit_seconds": plan.core_wall_limit_seconds,
            "core_wall_within_limit": None,
            "peak_rss_bytes": None,
            "peak_rss_run": None,
            "all_runs_done": False,
            "expected_wall": None,
        }
        night = cls(directory, data, roots)
        night.save()
        return night

    # --- bookkeeping ---

    def begin_invocation(self, *, resumed: bool, only: Sequence[str] | None) -> None:
        me = psutil.Process()
        self.data["driver"]["pid"] = me.pid
        self.data["driver"]["create_time"] = me.create_time()
        self.data["driver"]["invocations"].append(
            {
                "started_at": _utc(),
                "ended_at": None,
                "pid": me.pid,
                "resumed": resumed,
                "only": list(only) if only else None,
                "argv": list(sys.argv),
            }
        )
        for name, entry in self.runs.items():
            if entry["status"] == RUNNING:
                self.data["interruptions"].append(
                    {
                        "run": name,
                        "attempt": entry["attempts"],
                        "started_at": entry.get("started_at"),
                        "noticed_at": _utc(),
                        "note": "the previous driver ended while this run was executing",
                    }
                )
        self.data["state"] = RUNNING if self.data["outcome_code"] is None else self.state
        self.save()

    def end_invocation(self) -> None:
        self.data["driver"]["invocations"][-1]["ended_at"] = _utc()
        self.save()

    def peak_over_night(self) -> tuple[int | None, str | None]:
        best, who = None, None
        for name, entry in self.runs.items():
            peak = entry.get("peak_rss_bytes")
            if peak is not None and (best is None or peak > best):
                best, who = peak, name
        return best, who

    def core_wall(self, plan: MatrixPlan) -> float | None:
        """The walls of the core runs' completed attempts together (``None`` until at least
        one core run has completed)."""
        walls = [
            self.runs[name].get("wall_seconds")
            for name in plan.core_runs
            if self.runs[name]["status"] == COMPLETED
        ]
        return round(sum(walls), 3) if walls else None

    def refresh(self, plan: MatrixPlan) -> None:
        peak, who = self.peak_over_night()
        self.data["peak_rss_bytes"], self.data["peak_rss_run"] = peak, who
        core = self.core_wall(plan)
        self.data["core_wall_seconds"] = core
        both = all(self.runs[n]["status"] == COMPLETED for n in plan.core_runs)
        self.data["core_wall_within_limit"] = (
            (core <= plan.core_wall_limit_seconds) if both and core is not None else None
        )
        self.data["all_runs_done"] = all(
            e["status"] in (COMPLETED, KILLED_RSS) for e in self.runs.values()
        )

    def mark_killed(self, reason: str) -> None:
        self.data["outcome_code"] = KILLED_BY_EVIDENCE
        self.data["state"] = KILLED_BY_EVIDENCE
        self.data["kill_reason"] = reason
        self.data["finished_at"] = _utc()

    def mark_stopped(self, reason: str) -> None:
        if self.data["outcome_code"] is None:
            self.data["state"] = STOPPED
        self.data["stop_reason"] = reason

    def mark_finished(self) -> None:
        if self.data["outcome_code"] is None:
            self.data["state"] = FINISHED
        self.data["stop_reason"] = None
        self.data["finished_at"] = _utc()


# --- the extrapolation --------------------------------------------------------------------


def phase_seconds(phases: Mapping[str, Any], name: str) -> float | None:
    phase = phases.get(name) or {}
    start, end = phase.get("start"), phase.get("end")
    if not start or not end:
        return None
    return (
        datetime.fromisoformat(end.replace("Z", "+00:00"))
        - datetime.fromisoformat(start.replace("Z", "+00:00"))
    ).total_seconds()


def extrapolate(night: Night, plan: MatrixPlan) -> dict[str, Any] | None:
    """For a rehearsal subset: each completed run's wall split into a fixed part (r5py's
    import and the network build) and a routing part scaled **linearly in origins** to
    the full origin count; the core runs' extrapolated walls together against the limit.
    R5 routes origins in parallel over 8 threads, so a small subset under-uses the pool
    and the estimate is pessimistic."""
    n = night.data["origins"]["count"]
    full = night.data["origins"]["full_count"]
    if not night.data["origins"]["subset"] or n >= full:
        return None
    per_run: dict[str, dict[str, Any]] = {}
    for name, entry in night.runs.items():
        if entry["status"] != COMPLETED or entry.get("wall_seconds") is None:
            continue
        wall = float(entry["wall_seconds"])
        phases = entry.get("phases") or {}
        route = phases.get("route_seconds")
        fixed = phases.get("fixed_seconds")
        if route is None or fixed is None:
            fixed, route = 0.0, wall
        per_origin = route / n
        per_run[name] = {
            "origins": n,
            "wall_seconds": wall,
            "fixed_seconds": round(fixed, 3),
            "route_seconds": round(route, 3),
            "per_origin_seconds": round(per_origin, 4),
            "extrapolated_seconds": round(fixed + per_origin * full, 1),
            "network_cached_before": phases.get("network_cached_before"),
        }
    core = [per_run[c]["extrapolated_seconds"] for c in plan.core_runs if c in per_run]
    core_total = round(sum(core), 1) if len(core) == len(plan.core_runs) else None
    return {
        "method": (
            "linear in origins: wall = fixed (import + network build) + per-origin routing "
            "seconds x origins; the per-origin rate is measured on the subset and applied "
            "to the full origin count; R5 routes origins in parallel over 8 threads, so a "
            "subset smaller than the pool under-uses it and the estimate is pessimistic"
        ),
        "subset_origins": n,
        "full_origins": full,
        "runs": per_run,
        "core_extrapolated_seconds": core_total,
        "core_wall_limit_seconds": plan.core_wall_limit_seconds,
        "core_within_limit": (core_total <= plan.core_wall_limit_seconds)
        if core_total is not None
        else None,
        "all_runs_extrapolated_seconds": round(
            sum(r["extrapolated_seconds"] for r in per_run.values()), 1
        )
        if per_run
        else None,
    }


# --- the driver -----------------------------------------------------------------------------


def _phase_summary(record: RunRecord) -> dict[str, Any]:
    phases = record.phases or {}
    route = sum(
        s
        for name in phases
        if name.startswith("route:")
        if (s := phase_seconds(phases, name)) is not None
    )
    imp, build = phase_seconds(phases, "import"), phase_seconds(phases, "build")
    fixed = (imp or 0.0) + (build or 0.0)
    return {
        "import_seconds": imp,
        "build_seconds": build,
        "fixed_seconds": round(fixed, 3) if phases else None,
        "route_seconds": round(route, 3) if phases else None,
        "network_cached_before": (phases.get("build") or {}).get("network_cached_before"),
        "build_peak_rss_bytes": (phases.get("build") or {}).get("peak_rss_bytes"),
        "route_peak_rss_bytes": max(
            (p.get("peak_rss_bytes") or 0 for n, p in phases.items() if n.startswith("route:")),
            default=None,
        ),
    }


def _move_aside(run_dir: Path, attempt: int) -> str | None:
    if not run_dir.exists():
        return None
    target = run_dir.with_name(f"{run_dir.name}.attempt{attempt}")
    while target.exists():
        attempt += 1
        target = run_dir.with_name(f"{run_dir.name}.attempt{attempt}")
    shutil.move(str(run_dir), str(target))
    return target.name


def touch_cache(data_root: Path) -> int:
    """Touch r5py's cache files so its two-week expiry cannot rebuild the network mid-night.
    Returns how many files were touched."""
    cache = harness.cache_dir(data_root)
    if not cache.is_dir():
        return 0
    now = time.time()
    count = 0
    for path in cache.iterdir():
        # Only regular files: r5py's working copies of the inputs are symlinks into
        # intermediate/network/, and following them would touch the pipeline's files.
        if path.is_symlink() or not path.is_file():
            continue
        try:
            os.utime(path, (now, now))
        except OSError:
            continue
        count += 1
    return count


def keep_awake() -> bool:
    """Ask Windows not to sleep while this process runs (a per-process request, not a
    system setting; released when the process exits). ``False`` elsewhere."""
    if sys.platform != "win32":
        return False
    import ctypes  # noqa: PLC0415 - Windows only

    es_continuous, es_system_required = 0x80000000, 0x00000001
    return bool(ctypes.windll.kernel32.SetThreadExecutionState(es_continuous | es_system_required))


def run_matrix(
    plan: MatrixPlan,
    *,
    data_root: Path,
    toolchain: Toolchain,
    night_id_: str | None = None,
    origins_subset: int | None = None,
    only: Sequence[str] | None = None,
    continue_after_kill: bool = False,
    runner: Runner = harness.run,
    inputs: Mapping[str, str] | None = None,
    echo: Callable[[str], None] | None = None,
    now: datetime | None = None,
) -> Night:
    """Execute (or resume) a night. Returns the night; its state says how it ended."""
    from phillysim.routing.smoke import network_inputs  # noqa: PLC0415 - avoid a cycle

    if only:
        unknown = [name for name in only if name not in plan.run_names]
        if unknown:
            raise PlanError(f"--only names runs not in the plan: {unknown}")
    roots = harness.scrub_roots(data_root, toolchain)
    inputs = dict(inputs) if inputs is not None else network_inputs(data_root)
    windows = feed_windows(data_root, inputs)
    problems = check_feed_windows(plan, windows)
    if problems:
        raise PlanError(
            "the plan's dates are outside a feed's authoritative window: " + "; ".join(problems)
        )
    night_id_ = night_id_ or night_id(plan, origins_subset, now)
    directory = night_dir(data_root, night_id_)
    resumed = (directory / NIGHT_FILE).is_file()
    if resumed:
        night = Night.load(directory, roots)
        if night.data["plan"]["sha256"] != plan.sha256 or night.data["plan"]["name"] != plan.name:
            raise PlanError(f"night {night_id_} was started from a different plan file")
        if night.data["origins"]["subset"] != origins_subset:
            earlier = night.data["origins"]["subset"]
            raise PlanError(
                f"night {night_id_} was started with origins subset {earlier}, not {origins_subset}"
            )
        points = read_points(directory / POINTS_FILE)
        if continue_after_kill:
            night.data["continue_after_kill"] = True
    else:
        points = build_points(data_root, plan, origins_subset=origins_subset)
        night = Night.create(
            directory,
            plan,
            origins_subset=origins_subset,
            points=points,
            inputs=inputs,
            windows=windows,
            continue_after_kill=continue_after_kill,
            roots=roots,
            now=now,
        )
    log = (directory / DRIVER_LOG).open("a", encoding="utf-8")

    def say(line: str) -> None:
        log.write(f"{_utc()} {line}\n")
        log.flush()
        if echo:
            echo(line)

    try:
        say(
            f"night {night.id}: {'resuming' if resumed else 'starting'} plan {plan.name} "
            f"({plan.source} {plan.sha256[:12]}), {night.data['origins']['count']} origins x "
            f"{night.data['destinations']['count']} destinations, {len(plan.runs)} runs"
        )
        if night.data["outcome_code"] == KILLED_BY_EVIDENCE and not continue_after_kill:
            say(
                f"night {night.id}: already {KILLED_BY_EVIDENCE} ({night.data['kill_reason']}); "
                "not continuing without --continue-after-kill"
            )
            return night
        night.begin_invocation(resumed=resumed, only=only)
        touched = touch_cache(data_root)
        say(f"night {night.id}: touched {touched} r5py cache file(s)")
        for run in plan.runs:
            if only and run.name not in only:
                continue
            entry = night.runs[run.name]
            if entry["status"] == COMPLETED:
                say(f"run {run.name}: completed earlier ({entry.get('wall_seconds')} s); skipped")
                continue
            if entry["status"] == KILLED_RSS and entry["core"]:
                say(
                    f"run {run.name}: killed at the RSS line earlier (the evidence stands); "
                    "not re-run"
                )
                continue
            run_dir = directory / run.name
            aside = _move_aside(run_dir, entry["attempts"])
            if aside:
                say(f"run {run.name}: earlier attempt kept as {aside}")
                entry.setdefault("earlier_attempts", []).append(aside)
            entry["attempts"] += 1
            entry["status"] = RUNNING
            entry["started_at"] = _utc()
            entry["finished_at"] = None
            night.save()
            say(describe(run))
            plan_for_run = run_plan(plan, run, points, inputs, origins_subset=origins_subset)
            record = runner(
                plan_for_run,
                data_root=data_root,
                toolchain=toolchain,
                run_id=f"{night.id}/{run.name}",
                run_dir=run_dir,
                echo=say,
            )
            entry.update(
                {
                    "status": record.outcome,
                    "run_id": record.run_id,
                    "finished_at": record.finished_at,
                    "wall_seconds": record.wall_seconds,
                    "exit_code": record.exit_code,
                    "peak_rss_bytes": record.rss.get("peak_rss_bytes"),
                    "budget_crossed": record.rss.get("budget_crossed"),
                    "rss_samples": record.rss.get("samples"),
                    "error": record.error,
                    "output": record.output,
                    "phases": _phase_summary(record),
                }
            )
            if record.outcome == COMPLETED:
                info = finish_run_output(run_dir, points, run, plan.max_time_minutes)
                entry["matrix"] = info["matrix"]
                entry["sanity"] = info["sanity"]
                s = info["sanity"]
                say(
                    f"run {run.name}: matrix {info['matrix']['rows']} rows, values "
                    f"{info['matrix']['canonical_value_sha256'][:12]}; "
                    f"finite {s['finite_share']:.4f} "
                    f"({'meets' if s['finite_share_gate_met'] else 'BELOW'} the "
                    f"{FINITE_SHARE_GATE:.0%} gate), at censor {s['at_censor']}, "
                    f"missing rows {s['missing_rows']}"
                )
            night.refresh(plan)
            night.data["expected_wall"] = extrapolate(night, plan)
            night.save()
            if entry["core"] and record.outcome == KILLED_RSS:
                night.mark_killed(f"core run {run.name} killed at the RSS line: {record.error}")
                say(f"night {night.id}: {KILLED_BY_EVIDENCE}: {night.data['kill_reason']}")
                night.save()
                if not continue_after_kill:
                    break
                continue
            core = night.data["core_wall_seconds"]
            if entry["core"] and core is not None and core > plan.core_wall_limit_seconds:
                night.mark_killed(
                    f"core wall {core:.0f} s exceeds the limit "
                    f"{plan.core_wall_limit_seconds:.0f} s after {run.name}"
                )
                say(f"night {night.id}: {KILLED_BY_EVIDENCE}: {night.data['kill_reason']}")
                night.save()
                if not continue_after_kill:
                    break
                continue
            if record.outcome not in (COMPLETED, KILLED_RSS):
                night.mark_stopped(f"run {run.name} {record.outcome}: {record.error}")
                say(f"night {night.id}: stopped: {night.data['stop_reason']}")
                night.save()
                break
        else:
            night.refresh(plan)
            if night.data["all_runs_done"]:
                night.mark_finished()
                say(
                    f"night {night.id}: {night.state}; core wall "
                    f"{night.data['core_wall_seconds']} s; peak RSS "
                    f"{(night.data['peak_rss_bytes'] or 0) / 10**9:.2f} GB "
                    f"({night.data['peak_rss_run']})"
                )
            else:
                pending = [
                    n for n, e in night.runs.items() if e["status"] not in (COMPLETED, KILLED_RSS)
                ]
                night.mark_stopped(f"runs pending: {', '.join(pending)}")
                say(f"night {night.id}: stopped with runs pending: {', '.join(pending)}")
        night.end_invocation()
        return night
    finally:
        log.close()


# --- status (read-only) ---------------------------------------------------------------------


def _last_rss_sample(run_dir: Path) -> dict[str, Any] | None:
    path = run_dir / records.RSS_FILE
    if not path.is_file():
        return None
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - 4096))
        tail = handle.read().decode("utf-8", "replace").strip().splitlines()
    lines = [line for line in tail if line and not line.startswith("utc,")]
    if not lines:
        return None
    parts = lines[-1].split(",")
    if len(parts) != 3:
        return None
    return {"utc": parts[0], "elapsed_s": float(parts[1]), "rss_bytes": int(parts[2])}


def status(directory: Path) -> dict[str, Any]:
    """What ``route status`` reports: the night's state, whether its driver is alive, and
    per run its status, wall so far, and the last RSS sample. Reads only."""
    night = Night.load(directory)
    driver = night.data.get("driver") or {}
    pid, create_time = driver.get("pid"), driver.get("create_time")
    alive = False
    if pid:
        try:
            process = psutil.Process(int(pid))
            alive = process.is_running() and (
                create_time is None or abs(process.create_time() - float(create_time)) < 2
            )
        except psutil.Error:
            alive = False
    runs = []
    now = datetime.now(UTC)
    for name, entry in sorted(night.runs.items(), key=lambda item: item[1]["order"]):
        row = {
            "run": name,
            "order": entry["order"],
            "role": entry["role"],
            "core": entry["core"],
            "status": entry["status"],
            "attempts": entry["attempts"],
            "wall_seconds": entry.get("wall_seconds"),
            "peak_rss_bytes": entry.get("peak_rss_bytes"),
            "last_rss": None,
        }
        if entry["status"] == RUNNING and entry.get("started_at"):
            started = datetime.fromisoformat(entry["started_at"].replace("Z", "+00:00"))
            row["wall_seconds"] = round((now - started).total_seconds(), 1)
            row["last_rss"] = _last_rss_sample(directory / entry["dir"])
        runs.append(row)
    return {
        "night_id": night.id,
        "state": night.state,
        "outcome_code": night.data.get("outcome_code"),
        "kill_reason": night.data.get("kill_reason"),
        "stop_reason": night.data.get("stop_reason"),
        "driver_pid": pid,
        "driver_alive": alive,
        "started_at": night.data.get("started_at"),
        "updated_at": night.data.get("updated_at"),
        "finished_at": night.data.get("finished_at"),
        "core_wall_seconds": night.data.get("core_wall_seconds"),
        "core_wall_limit_seconds": night.data.get("core_wall_limit_seconds"),
        "peak_rss_bytes": night.data.get("peak_rss_bytes"),
        "expected_wall": night.data.get("expected_wall"),
        "runs": runs,
    }


def status_lines(report: Mapping[str, Any]) -> list[str]:
    out = [
        f"night {report['night_id']}: {report['state']}"
        + (
            f" ({report['outcome_code']}: {report['kill_reason']})"
            if report.get("outcome_code")
            else ""
        )
        + (f" ({report['stop_reason']})" if report.get("stop_reason") else "")
        + f"; driver pid {report['driver_pid']} "
        + ("alive" if report["driver_alive"] else "not running")
    ]
    for row in report["runs"]:
        wall = f"{row['wall_seconds']:.0f} s" if row.get("wall_seconds") is not None else "-"
        peak = f"{row['peak_rss_bytes'] / 10**9:.2f} GB" if row.get("peak_rss_bytes") else "-"
        line = (
            f"  {row['order']}. {row['run']:<24} {row['status']:<12} wall {wall:>8}  peak {peak:>8}"
        )
        if row["core"]:
            line += "  core"
        if row.get("last_rss"):
            last = row["last_rss"]
            line += f"  last sample {last['rss_bytes'] / 10**9:.2f} GB at {last['elapsed_s']:.0f} s"
        out.append(line)
    core = report.get("core_wall_seconds")
    if core is not None:
        out.append(f"  core wall {core:.0f} s of {report['core_wall_limit_seconds']:.0f} s")
    if report.get("peak_rss_bytes"):
        out.append(f"  peak RSS over the night {report['peak_rss_bytes'] / 10**9:.2f} GB")
    expected = report.get("expected_wall")
    if expected and expected.get("core_extrapolated_seconds") is not None:
        out.append(
            f"  extrapolated core wall at {expected['full_origins']} origins: "
            f"{expected['core_extrapolated_seconds'] / 3600:.2f} h "
            f"({'within' if expected['core_within_limit'] else 'OVER'} the "
            f"{expected['core_wall_limit_seconds'] / 3600:.0f} h limit)"
        )
    return out
