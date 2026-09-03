"""Run plans and run records: the fixed, scrubbed shape every routing run leaves (EP-13).

A run lives at ``<data root>/runs/routing/<run-id>/`` with ``<run-id>`` =
``<UTC timestamp>-<plan slug>`` and holds:

* ``plan.json``: what was asked (modes, walking speed, departure and window,
  percentiles, the maximum trip time, the origin and destination sets with
  their counts and coordinates, the inputs as data-root-relative paths);
* ``record.json``: what happened (outcome ``completed`` / ``killed-rss`` /
  ``failed`` / ``cancelled``; wall seconds overall and per phase; peak RSS and
  the second it occurred; whether the 20 GB budget was crossed; the toolchain
  digests and versions; the inputs' digests; the output's byte digest and
  canonicalized-value digest);
* ``rss.csv``: the sampler's time series; ``log.txt``: the child's stdout and
  stderr; ``travel_times.csv``: the output table; ``child.json``: the child's
  environment overrides and r5py arguments as recorded (scrubbed).

Paths inside every file are relative to the data root; the data root and
the repository root are scrubbed to ``<data-root>`` and ``<repo-root>``
like the state file's error text (``phillysim.runner``). ``data/runs/`` is
gitignored. The **canonicalized-value digest** is the SHA-256 of the table's
rows in key order with sorted columns and normalized values (integral floats
as integers, missing as null), so two runs that agree in value agree in
digest whatever the row order or the float formatting; the byte digest is the
SHA-256 of the file as written.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import pandas as pd

RUNS_DIR = "runs/routing"
RECORD_SCHEMA_VERSION = 1
OUTCOMES: tuple[str, ...] = ("completed", "killed-rss", "failed", "cancelled")
COMPLETED, KILLED_RSS, FAILED, CANCELLED = OUTCOMES

PLAN_FILE = "plan.json"
RECORD_FILE = "record.json"
RSS_FILE = "rss.csv"
LOG_FILE = "log.txt"
CHILD_FILE = "child.json"
PHASES_FILE = "phases.json"
ERROR_FILE = "error.json"
OUTPUT_FILE = "travel_times.csv"
OUTPUT_KEY: tuple[str, ...] = ("mode", "from_id", "to_id")

MODES: tuple[str, ...] = ("walk", "walk_transit")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")


def check_slug(slug: str) -> str:
    if not _SLUG_RE.match(slug):
        raise ValueError(f"plan slug {slug!r}: lower-case letters, digits, hyphens; <= 48 chars")
    return slug


@dataclass(frozen=True)
class Point:
    id: str
    lon: float
    lat: float


@dataclass(frozen=True)
class RunPlan:
    """What a run is asked to do. Departure is a naive local time in ``time_zone``."""

    slug: str
    modes: tuple[str, ...]
    speed_walking_kmh: float
    departure: str  # "YYYY-MM-DDTHH:MM", local
    time_zone: str
    window_minutes: int
    percentiles: tuple[int, ...]
    max_time_minutes: int
    origins: tuple[Point, ...]
    destinations: tuple[Point, ...]
    inputs: Mapping[str, str]  # label -> data-root-relative path
    origins_description: str = ""
    destinations_description: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        check_slug(self.slug)
        unknown = set(self.modes) - set(MODES)
        if unknown or not self.modes:
            raise ValueError(f"modes must be a non-empty subset of {MODES}, not {self.modes}")
        if self.window_minutes < 1 or self.max_time_minutes < 1 or self.speed_walking_kmh <= 0:
            raise ValueError("window, max_time, and walking speed must be positive")
        datetime.strptime(self.departure, "%Y-%m-%dT%H:%M")  # validates
        if not self.origins or not self.destinations:
            raise ValueError("a plan needs at least one origin and one destination")
        for label, rel in self.inputs.items():
            if not is_data_root_relative(rel):
                raise ValueError(f"input {label!r}: {rel!r} is not a data-root-relative path")

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "modes": list(self.modes),
            "speed_walking_kmh": self.speed_walking_kmh,
            "departure": self.departure,
            "time_zone": self.time_zone,
            "window_minutes": self.window_minutes,
            "percentiles": list(self.percentiles),
            "max_time_minutes": self.max_time_minutes,
            "origins": {
                "description": self.origins_description,
                "count": len(self.origins),
                "points": [asdict(p) for p in self.origins],
            },
            "destinations": {
                "description": self.destinations_description,
                "count": len(self.destinations),
                "points": [asdict(p) for p in self.destinations],
            },
            "inputs": dict(self.inputs),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RunPlan:
        return cls(
            slug=data["slug"],
            modes=tuple(data["modes"]),
            speed_walking_kmh=float(data["speed_walking_kmh"]),
            departure=data["departure"],
            time_zone=data["time_zone"],
            window_minutes=int(data["window_minutes"]),
            percentiles=tuple(int(p) for p in data["percentiles"]),
            max_time_minutes=int(data["max_time_minutes"]),
            origins=tuple(Point(**p) for p in data["origins"]["points"]),
            destinations=tuple(Point(**p) for p in data["destinations"]["points"]),
            inputs=dict(data["inputs"]),
            origins_description=data["origins"].get("description", ""),
            destinations_description=data["destinations"].get("description", ""),
            note=data.get("note", ""),
        )


def is_data_root_relative(rel: str) -> bool:
    """Relative on every platform (no POSIX root, no drive letter, no ``..`` segment)."""
    if PurePosixPath(rel).is_absolute() or PureWindowsPath(rel).is_absolute():
        return False
    if PureWindowsPath(rel).drive or rel.startswith(("/", "\\")):
        return False
    return ".." not in PurePosixPath(rel.replace("\\", "/")).parts


def utc_stamp(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def run_id(slug: str, now: datetime | None = None) -> str:
    """``<UTC timestamp>-<plan slug>``."""
    return f"{utc_stamp(now)}-{check_slug(slug)}"


def run_dir(data_root: Path, run_id_: str) -> Path:
    return data_root / RUNS_DIR / run_id_


# --- scrubbing -----------------------------------------------------------------------------


def scrub(text: str, roots: Mapping[str, Path]) -> str:
    """Replace every form of each root path (native, doubled-backslash, POSIX) with its
    placeholder, longest paths first so a nested root is not half-replaced."""
    ordered = sorted(roots.items(), key=lambda item: -len(str(item[1])))
    for placeholder, root in ordered:
        native = str(root)
        for form in dict.fromkeys((native.replace("\\", "\\\\"), native, root.as_posix())):
            if form:
                text = text.replace(form, placeholder)
    return text


def scrub_value(value: Any, roots: Mapping[str, Path]) -> Any:
    """Scrub every string inside a JSON-like value."""
    if isinstance(value, str):
        return scrub(value, roots)
    if isinstance(value, Mapping):
        return {k: scrub_value(v, roots) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [scrub_value(v, roots) for v in value]
    return value


# --- digests -------------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_value(value: Any) -> Any:
    """Normalize one cell: missing -> ``None``; integral floats -> ``int``; other floats
    rounded to six decimals; numpy scalars -> Python scalars; everything else as is."""
    if value is None:
        return None
    if hasattr(value, "item") and not isinstance(value, str | bytes):
        value = value.item()
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        if value.is_integer():
            return int(value)
        return round(value, 6)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def canonical_rows(frame: pd.DataFrame, key: Sequence[str] = OUTPUT_KEY) -> list[dict[str, Any]]:
    """The frame's rows in ``key`` order with sorted columns and canonical values."""
    missing = [k for k in key if k not in frame.columns]
    if missing:
        raise ValueError(f"the table lacks key column(s) {missing}")
    ordered = frame.sort_values(list(key), kind="stable").reset_index(drop=True)
    columns = sorted(ordered.columns)
    return [
        {column: canonical_value(row[column]) for column in columns}
        for row in ordered.to_dict("records")
    ]


def canonical_value_digest(frame: pd.DataFrame, key: Sequence[str] = OUTPUT_KEY) -> str:
    payload = json.dumps(canonical_rows(frame, key), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_output(frame: pd.DataFrame, path: Path, key: Sequence[str] = OUTPUT_KEY) -> None:
    """Write the output table as CSV in canonical row order with canonical values (so the
    byte digest of two value-identical runs agrees too)."""
    rows = canonical_rows(frame, key)
    columns = sorted(frame.columns)
    ordered = list(key) + [c for c in columns if c not in key]
    lines = [",".join(ordered)]
    for row in rows:
        lines.append(",".join("" if row[c] is None else str(row[c]) for c in ordered))
    path.write_text("\n".join(lines) + "\n", "utf-8", newline="\n")


def read_output(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"mode": "string", "from_id": "string", "to_id": "string"})


# --- the record ----------------------------------------------------------------------------


@dataclass
class RunRecord:
    """The outcome of one run, in the shape ``record.json`` takes."""

    run_id: str
    slug: str
    outcome: str
    started_at: str
    finished_at: str | None
    wall_seconds: float | None
    exit_code: int | None
    phases: dict[str, Any] = field(default_factory=dict)
    rss: dict[str, Any] = field(default_factory=dict)
    toolchain: dict[str, Any] = field(default_factory=dict)
    versions: dict[str, str | None] = field(default_factory=dict)
    inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    output: dict[str, Any] | None = None
    error: str | None = None
    files: dict[str, str] = field(default_factory=dict)
    schema_version: int = RECORD_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {OUTCOMES}, not {self.outcome!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "slug": self.slug,
            "outcome": self.outcome,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "wall_seconds": self.wall_seconds,
            "exit_code": self.exit_code,
            "phases": self.phases,
            "rss": self.rss,
            "toolchain": self.toolchain,
            "versions": self.versions,
            "inputs": self.inputs,
            "output": self.output,
            "error": self.error,
            "files": self.files,
        }


def write_json(path: Path, payload: Mapping[str, Any], roots: Mapping[str, Path]) -> None:
    """Canonical JSON (two-space indent, sorted keys), every string scrubbed."""
    path.write_text(
        json.dumps(scrub_value(dict(payload), roots), indent=2, sort_keys=True) + "\n", "utf-8"
    )


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8"))


def list_runs(data_root: Path) -> list[Path]:
    base = data_root / RUNS_DIR
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir())


def input_digests(data_root: Path, inputs: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for label, rel in inputs.items():
        path = data_root / rel
        out[label] = {
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    return out


def outputs_agree(records: Iterable[Mapping[str, Any]]) -> tuple[bool, list[str | None]]:
    """Do these records' canonicalized-value digests all agree? Returns the verdict and the
    digests in order (``None`` for a record without an output)."""
    digests = [(r.get("output") or {}).get("canonical_value_sha256") for r in records]
    present = [d for d in digests if d is not None]
    return bool(present) and len(set(present)) == 1 and len(present) == len(digests), digests
