"""Matrix plans: the spike's runs written down as data before they run (EP-14; ADR-0008).

A **matrix plan** is a tracked JSON file under ``phillysim/routing/plans/`` that
names every run the M3 criteria need, with the parameters of ADR-0008 and
methodology.md "Travel model" verbatim and **no path**: the origin and
destination sets are named by curated table and column, the transit feeds and
the street network come from the ``network`` stage's report at run time. Each
run has a name, one mode, a walking speed, a date, a departure time, a window
(one departure per minute, so the window in minutes is the departure count),
and a role (``core``, ``repeat`` of an earlier run with identical parameters,
``sensitivity``, ``saturday``). The core runs are listed first and the ≤ 8 h
wall criterion applies to their walls together.

:func:`load_plan` parses and validates a plan; :func:`build_points` reads the
origins and destinations once from the curated tables (the spine's population-
weighted centers, the retailer layer's provider coordinates; both leave the
analysis CRS as WGS 84 only here, at the r5py boundary, ADR-0007) so every run
of a night routes the same points; :func:`feed_windows` reads ``feed_info.txt``
from the unwrapped feed zips and :func:`check_feed_windows` refuses a plan
whose dates fall outside either feed's authoritative window; :func:`run_plan`
turns one run of the plan into the harness's :class:`~phillysim.routing.records.RunPlan`.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from phillysim.destinations import SNAP_RETAILERS
from phillysim.routing import records
from phillysim.routing.records import MODES, Point, RunPlan, check_slug
from phillysim.spine import SPINE

PLANS_DIR = Path(__file__).parent / "plans"
PLAN_SCHEMA_VERSION = 1
DEFAULT_PLAN = "m3-spike.json"
ROLES: tuple[str, ...] = ("core", "repeat", "sensitivity", "saturday")
#: The curated tables a plan may name (no path in the plan: the name resolves here).
TABLES: Mapping[str, str] = {"tracts_spine": SPINE, "snap_retailers": SNAP_RETAILERS}
POINTS_FILE = "points.parquet"
ROLE_ORIGIN, ROLE_DESTINATION = "origin", "destination"
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class PlanError(ValueError):
    """The plan file is not a valid matrix plan."""


@dataclass(frozen=True)
class MatrixRun:
    name: str
    mode: str
    speed_walking_kmh: float
    date: str  # ISO date
    departure_time: str  # HH:MM local
    window_minutes: int
    role: str
    repeat_of: str | None = None

    @property
    def departure(self) -> str:
        return f"{self.date}T{self.departure_time}"

    @property
    def departures(self) -> int:
        """One departure per minute of the window (methodology.md)."""
        return self.window_minutes

    def parameters(self) -> dict[str, Any]:
        """What must agree between a run and its repeat."""
        return {
            "mode": self.mode,
            "speed_walking_kmh": self.speed_walking_kmh,
            "date": self.date,
            "departure_time": self.departure_time,
            "window_minutes": self.window_minutes,
        }

    def to_dict(self) -> dict[str, Any]:
        out = {"name": self.name, **self.parameters(), "role": self.role}
        if self.repeat_of:
            out["repeat_of"] = self.repeat_of
        return out


@dataclass(frozen=True)
class PointSet:
    table: str
    id: str
    lon: str
    lat: str
    count: int
    description: str = ""

    @property
    def path(self) -> str:
        return TABLES[self.table]

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "id": self.id,
            "lon": self.lon,
            "lat": self.lat,
            "count": self.count,
            "description": self.description,
        }


@dataclass(frozen=True)
class MatrixPlan:
    name: str
    title: str
    time_zone: str
    dates: Mapping[str, str]
    percentiles: tuple[int, ...]
    max_time_minutes: int
    snap_to_network: bool
    origins: PointSet
    destinations: PointSet
    rehearsal_origins: tuple[str, ...]
    core_runs: tuple[str, ...]
    core_wall_limit_hours: float
    runs: tuple[MatrixRun, ...]
    references: tuple[str, ...] = ()
    source: str = ""  # the file name, for records
    sha256: str = ""
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def core_wall_limit_seconds(self) -> float:
        return self.core_wall_limit_hours * 3600

    @property
    def run_names(self) -> tuple[str, ...]:
        return tuple(r.name for r in self.runs)

    def run(self, name: str) -> MatrixRun:
        for r in self.runs:
            if r.name == name:
                return r
        raise KeyError(name)

    def is_core(self, name: str) -> bool:
        return name in self.core_runs

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PLAN_SCHEMA_VERSION,
            "name": self.name,
            "title": self.title,
            "references": list(self.references),
            "time_zone": self.time_zone,
            "dates": dict(self.dates),
            "percentiles": list(self.percentiles),
            "max_time_minutes": self.max_time_minutes,
            "snap_to_network": self.snap_to_network,
            "origins": self.origins.to_dict(),
            "destinations": self.destinations.to_dict(),
            "rehearsal_origins": list(self.rehearsal_origins),
            "core_runs": list(self.core_runs),
            "core_wall_limit_hours": self.core_wall_limit_hours,
            "runs": [r.to_dict() for r in self.runs],
        }


# --- loading and validation ------------------------------------------------------------------


def plan_path(name_or_path: str | Path) -> Path:
    """A plan given as a path, or by file name under the package's ``plans/`` directory."""
    candidate = Path(name_or_path)
    if candidate.is_file():
        return candidate
    packaged = PLANS_DIR / str(name_or_path)
    if packaged.is_file():
        return packaged
    raise PlanError(
        f"no plan file {name_or_path!r} (not a file, and not under {PLANS_DIR.name}/: "
        f"{', '.join(sorted(p.name for p in PLANS_DIR.glob('*.json')))})"
    )


def _require(data: Mapping[str, Any], key: str, kind: type | tuple[type, ...]) -> Any:
    if key not in data:
        raise PlanError(f"plan lacks {key!r}")
    value = data[key]
    if not isinstance(value, kind) or isinstance(value, bool) and kind is not bool:
        raise PlanError(f"plan {key!r} must be {kind}, not {type(value).__name__}")
    return value


def _point_set(data: Mapping[str, Any], label: str) -> PointSet:
    if not isinstance(data, Mapping):
        raise PlanError(f"{label} must be an object")
    table = _require(data, "table", str)
    if table not in TABLES:
        raise PlanError(f"{label}: unknown table {table!r} (one of {sorted(TABLES)})")
    for key in ("id", "lon", "lat"):
        _require(data, key, str)
    count = _require(data, "count", int)
    if count < 1:
        raise PlanError(f"{label}: count must be positive")
    return PointSet(
        table, data["id"], data["lon"], data["lat"], count, str(data.get("description", ""))
    )


def _iso_date(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise PlanError(f"{label}: date must be an ISO string")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise PlanError(f"{label}: {value!r} is not an ISO date") from exc


def _run(data: Mapping[str, Any], index: int) -> MatrixRun:
    label = f"runs[{index}]"
    if not isinstance(data, Mapping):
        raise PlanError(f"{label} must be an object")
    name = _require(data, "name", str)
    try:
        check_slug(name)
    except ValueError as exc:
        raise PlanError(f"{label}: {exc}") from exc
    mode = _require(data, "mode", str)
    if mode not in MODES:
        raise PlanError(f"{label} ({name}): mode must be one of {MODES}, not {mode!r}")
    speed = _require(data, "speed_walking_kmh", int | float)
    if speed <= 0:
        raise PlanError(f"{label} ({name}): walking speed must be positive")
    day = _iso_date(data.get("date"), f"{label} ({name})")
    departure_time = _require(data, "departure_time", str)
    if not _TIME_RE.match(departure_time):
        raise PlanError(f"{label} ({name}): departure_time must be HH:MM, not {departure_time!r}")
    window = _require(data, "window_minutes", int)
    if window < 1:
        raise PlanError(f"{label} ({name}): window_minutes must be >= 1")
    role = _require(data, "role", str)
    if role not in ROLES:
        raise PlanError(f"{label} ({name}): role must be one of {ROLES}, not {role!r}")
    repeat_of = data.get("repeat_of")
    if (role == "repeat") != (repeat_of is not None):
        raise PlanError(f"{label} ({name}): role 'repeat' and 'repeat_of' go together")
    return MatrixRun(name, mode, float(speed), day, departure_time, window, role, repeat_of)


def parse_plan(data: Mapping[str, Any], *, source: str = "", sha256: str = "") -> MatrixPlan:
    if not isinstance(data, Mapping):
        raise PlanError("the plan must be a JSON object")
    if data.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise PlanError(f"plan schema_version must be {PLAN_SCHEMA_VERSION}")
    name = _require(data, "name", str)
    check_slug(name)
    time_zone = _require(data, "time_zone", str)
    dates = _require(data, "dates", Mapping)
    dates = {k: _iso_date(v, f"dates.{k}") for k, v in dates.items()}
    percentiles = tuple(int(p) for p in _require(data, "percentiles", list))
    if not percentiles or any(p < 1 or p > 99 for p in percentiles):
        raise PlanError("percentiles must be a non-empty list of integers in 1..99")
    max_time = _require(data, "max_time_minutes", int)
    if max_time < 1:
        raise PlanError("max_time_minutes must be positive")
    snap = _require(data, "snap_to_network", bool)
    origins = _point_set(_require(data, "origins", Mapping), "origins")
    destinations = _point_set(_require(data, "destinations", Mapping), "destinations")
    rehearsal = tuple(str(g) for g in _require(data, "rehearsal_origins", list))
    if len(set(rehearsal)) != len(rehearsal):
        raise PlanError("rehearsal_origins repeat an ID")
    runs = tuple(_run(r, i) for i, r in enumerate(_require(data, "runs", list)))
    if not runs:
        raise PlanError("the plan needs at least one run")
    names = [r.name for r in runs]
    if len(set(names)) != len(names):
        raise PlanError(f"run names repeat: {sorted(n for n in names if names.count(n) > 1)}")
    for i, r in enumerate(runs):
        if r.repeat_of is not None:
            earlier = {e.name: e for e in runs[:i]}
            if r.repeat_of not in earlier:
                raise PlanError(f"run {r.name}: repeat_of {r.repeat_of!r} is not an earlier run")
            if earlier[r.repeat_of].parameters() != r.parameters():
                raise PlanError(f"run {r.name}: parameters differ from its original {r.repeat_of}")
        if r.date not in dates.values():
            raise PlanError(f"run {r.name}: date {r.date} is not one of the plan's dates")
    core = tuple(str(c) for c in _require(data, "core_runs", list))
    if not core or any(c not in names for c in core):
        raise PlanError(f"core_runs must name runs of the plan: {core}")
    if tuple(names[: len(core)]) != core:
        raise PlanError("the core runs must come first, in order")
    limit = _require(data, "core_wall_limit_hours", int | float)
    if limit <= 0:
        raise PlanError("core_wall_limit_hours must be positive")
    known = {
        "schema_version",
        "name",
        "title",
        "references",
        "time_zone",
        "dates",
        "percentiles",
        "max_time_minutes",
        "snap_to_network",
        "origins",
        "destinations",
        "rehearsal_origins",
        "core_runs",
        "core_wall_limit_hours",
        "runs",
    }
    return MatrixPlan(
        name=name,
        title=str(data.get("title", "")),
        time_zone=time_zone,
        dates=dates,
        percentiles=percentiles,
        max_time_minutes=max_time,
        snap_to_network=snap,
        origins=origins,
        destinations=destinations,
        rehearsal_origins=rehearsal,
        core_runs=core,
        core_wall_limit_hours=float(limit),
        runs=runs,
        references=tuple(str(r) for r in data.get("references", [])),
        source=source,
        sha256=sha256,
        extra={k: v for k, v in data.items() if k not in known},
    )


def load_plan(name_or_path: str | Path) -> MatrixPlan:
    path = plan_path(name_or_path)
    try:
        data = json.loads(path.read_text("utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanError(f"{path.name}: not JSON ({exc})") from exc
    return parse_plan(data, source=path.name, sha256=records.sha256_file(path))


# --- the points ------------------------------------------------------------------------------


def _read_points(data_root: Path, spec: PointSet, label: str) -> pd.DataFrame:
    path = data_root / spec.path
    if not path.is_file():
        raise FileNotFoundError(f"{label}: {spec.path} is missing (run `phillysim run` first)")
    frame = pd.read_parquet(path, columns=[spec.id, spec.lon, spec.lat])
    frame = frame.rename(columns={spec.id: "id", spec.lon: "lon", spec.lat: "lat"})
    frame["id"] = frame["id"].astype(str)
    if frame["id"].duplicated().any():
        raise PlanError(f"{label}: {spec.table}.{spec.id} is not unique")
    if frame[["lon", "lat"]].isna().any().any():
        raise PlanError(f"{label}: {spec.table} has a missing coordinate")
    if len(frame) != spec.count:
        raise PlanError(f"{label}: {spec.table} has {len(frame)} rows, the plan says {spec.count}")
    return frame.sort_values("id", kind="stable").reset_index(drop=True)


def origin_order(ids: Sequence[str], rehearsal: Sequence[str]) -> list[str]:
    """The rehearsal origins first (in the plan's order), then the rest in sorted ID order:
    ``--origins-subset N`` takes the first N, so N = the rehearsal count is exactly the
    rehearsal set."""
    present = set(ids)
    missing = [g for g in rehearsal if g not in present]
    if missing:
        raise PlanError(f"rehearsal origins not in the origin table: {missing}")
    rest = sorted(g for g in ids if g not in set(rehearsal))
    return [*rehearsal, *rest]


def build_points(
    data_root: Path, plan: MatrixPlan, *, origins_subset: int | None = None
) -> pd.DataFrame:
    """One table of every point a night routes: ``role`` (``origin`` / ``destination``),
    ``id``, ``lon``, ``lat`` (WGS 84 as the curated tables carry them), origins in
    :func:`origin_order` (subset applied), destinations in ID order."""
    origins = _read_points(data_root, plan.origins, "origins")
    destinations = _read_points(data_root, plan.destinations, "destinations")
    order = origin_order(list(origins["id"]), plan.rehearsal_origins)
    if origins_subset is not None:
        if origins_subset < 1 or origins_subset > len(order):
            raise PlanError(f"--origins-subset must be in 1..{len(order)}, not {origins_subset}")
        order = order[:origins_subset]
    origins = origins.set_index("id").loc[order].reset_index()
    origins.insert(0, "role", ROLE_ORIGIN)
    destinations.insert(0, "role", ROLE_DESTINATION)
    return pd.concat([origins, destinations], ignore_index=True)[["role", "id", "lon", "lat"]]


def write_points(points: pd.DataFrame, path: Path) -> None:
    points.to_parquet(path, index=False)


def read_points(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def points_of(points: pd.DataFrame, role: str) -> tuple[Point, ...]:
    part = points[points["role"] == role]
    return tuple(Point(str(r.id), float(r.lon), float(r.lat)) for r in part.itertuples(index=False))


# --- the feeds' authoritative windows ---------------------------------------------------------


def feed_window(zip_path: Path) -> dict[str, str | None]:
    """``feed_info.txt``'s dates from one feed zip (ISO dates; ``None`` where absent)."""
    with zipfile.ZipFile(zip_path) as feed:
        if "feed_info.txt" not in feed.namelist():
            return {"feed_start_date": None, "feed_end_date": None, "feed_version": None}
        with feed.open("feed_info.txt") as raw:
            rows = list(csv.DictReader(io.TextIOWrapper(raw, "utf-8-sig")))
    info = rows[0] if rows else {}

    def iso(value: str | None) -> str | None:
        value = (value or "").strip()
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}" if len(value) == 8 else None

    return {
        "feed_start_date": iso(info.get("feed_start_date")),
        "feed_end_date": iso(info.get("feed_end_date")),
        "feed_version": (info.get("feed_version") or "").strip() or None,
    }


def feed_windows(data_root: Path, inputs: Mapping[str, str]) -> dict[str, dict[str, str | None]]:
    """Per ``gtfs*`` input label, its window."""
    return {
        label: feed_window(data_root / rel)
        for label, rel in sorted(inputs.items())
        if label.startswith("gtfs")
    }


def check_feed_windows(
    plan: MatrixPlan, windows: Mapping[str, Mapping[str, str | None]]
) -> list[str]:
    """Problems: a run date outside a feed's authoritative window, or a feed without one."""
    problems: list[str] = []
    dates = sorted({r.date for r in plan.runs if r.mode == "walk_transit"})
    for label, window in sorted(windows.items()):
        start, end = window.get("feed_start_date"), window.get("feed_end_date")
        if not start or not end:
            problems.append(f"{label}: feed_info.txt carries no authoritative window")
            continue
        for day in dates:
            if not start <= day <= end:
                problems.append(f"{label}: {day} is outside the feed's window {start}..{end}")
    return problems


# --- one run of the plan as a harness plan -------------------------------------------------


def run_plan(
    plan: MatrixPlan,
    run: MatrixRun,
    points: pd.DataFrame,
    inputs: Mapping[str, str],
    *,
    origins_subset: int | None = None,
) -> RunPlan:
    origins = points_of(points, ROLE_ORIGIN)
    subset = f" (rehearsal subset of {origins_subset})" if origins_subset else ""
    return RunPlan(
        slug=run.name,
        modes=(run.mode,),
        speed_walking_kmh=run.speed_walking_kmh,
        departure=run.departure,
        time_zone=plan.time_zone,
        window_minutes=run.window_minutes,
        percentiles=plan.percentiles,
        max_time_minutes=plan.max_time_minutes,
        origins=origins,
        destinations=points_of(points, ROLE_DESTINATION),
        inputs=dict(inputs),
        origins_description=f"{plan.origins.description}{subset}",
        destinations_description=plan.destinations.description,
        note=f"{plan.name} run {run.name} ({run.role}"
        + (f" of {run.repeat_of}" if run.repeat_of else "")
        + f"); {run.departures} departure(s) from {run.departure} {plan.time_zone}",
        snap_to_network=plan.snap_to_network,
    )


def describe(run: MatrixRun) -> str:
    when = datetime.strptime(run.departure, "%Y-%m-%dT%H:%M").strftime("%a %Y-%m-%d %H:%M")
    return (
        f"{run.name}: {run.mode} at {run.speed_walking_kmh} km/h, {when}, "
        f"{run.departures} departure(s) ({run.window_minutes} min window), {run.role}"
        + (f" of {run.repeat_of}" if run.repeat_of else "")
    )
