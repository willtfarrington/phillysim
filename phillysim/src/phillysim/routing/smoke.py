"""The smoke route (EP-13): the project's first JVM run, three times.

One origin, the spine center (CenPop's population-weighted center) of the
tract containing City Hall (``42101000500``, confirmed against the spine on
2026-09-03), to one destination, the supermarket-format retailer nearest to it
by the QA slice's rule (planar distance in the analysis CRS); ``TravelTimeMatrix``
for walk at 4.8 km/h and for walk+transit at 4.8 km/h on the pinned Wednesday
(ADR-0008: 2026-09-23) with a 60-minute window from 08:00, percentiles 50 and
85, ``max_time`` 120 minutes, on EP-12's clipped network and the two SEPTA feed
zips. Run three times in a row, each run its own record; the three
canonicalized-value digests are compared (the first determinism observation,
recorded whichever way it goes) and every RSS sample must stay under the kill
line. ``single_departure`` narrows the window to one minute for EP-15's hand
check (r5py warns below five minutes; the warning is in the log).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import geopandas as gpd

from phillysim.destinations import SNAP_RETAILERS
from phillysim.network import NETWORK_DIR, NETWORK_REPORT
from phillysim.routing import harness, records
from phillysim.routing.records import Point, RunPlan, RunRecord
from phillysim.routing.sampler import KILL_BYTES
from phillysim.routing.toolchain import Toolchain
from phillysim.spine import ANALYSIS_CRS, SPINE, centroids_in

#: ADR-0008 calendar: the pinned typical Wednesday and Saturday, America/New_York.
PINNED_WEDNESDAY = date(2026, 9, 23)
PINNED_SATURDAY = date(2026, 9, 26)
TIME_ZONE = "America/New_York"
#: methodology.md: network walk at 4.8 km/h (r5py's default is 3.6 and is always overridden).
WALK_SPEED_KMH = 4.8
PERCENTILES: tuple[int, ...] = (50, 85)
MAX_TIME_MINUTES = 120
WINDOW_MINUTES = 60
DEPARTURE_TIME = "08:00"
CITY_HALL_TRACT = "42101000500"
SLUG = "smoke"
SINGLE_DEPARTURE_SLUG = "smoke-single"
REPEATS = 3


def network_inputs(data_root: Path) -> dict[str, str]:
    """The routing inputs as data-root-relative paths, from the ``network`` stage's report."""
    report = json.loads((data_root / NETWORK_REPORT).read_text("utf-8"))
    inputs = {"osm": f"{NETWORK_DIR}/{report['osm']['file']}"}
    for feed in sorted(report["gtfs"]):  # "google_bus.zip", "google_rail.zip"
        label = feed.removeprefix("google_").removesuffix(".zip")
        inputs[f"gtfs_{label}"] = f"{NETWORK_DIR}/{feed}"
    for label, rel in inputs.items():
        if not (data_root / rel).is_file():
            raise FileNotFoundError(f"{label}: {rel} is missing (run `phillysim run` first)")
    return inputs


def smoke_endpoints(data_root: Path, tract: str = CITY_HALL_TRACT) -> tuple[Point, Point, float]:
    """The origin (the tract's spine center) and the destination (the nearest
    supermarket-format retailer, planar in the analysis CRS), plus the distance in metres."""
    spine = gpd.read_parquet(data_root / SPINE)
    row = spine[spine["geoid"] == tract]
    if len(row) != 1:
        raise ValueError(f"tract {tract} is not in the spine")
    center = centroids_in(row, ANALYSIS_CRS).iloc[0]
    retailers = gpd.read_parquet(data_root / SNAP_RETAILERS)
    supermarkets = retailers[retailers["supermarket_format"]].to_crs(ANALYSIS_CRS)
    if supermarkets.empty:
        raise ValueError("no supermarket-format retailer in the layer")
    distances = supermarkets.geometry.distance(center)
    nearest = supermarkets.loc[distances.idxmin()]
    origin = Point(tract, float(row["centroid_lon"].iloc[0]), float(row["centroid_lat"].iloc[0]))
    destination = Point(
        str(nearest["site_id"]), float(nearest["longitude"]), float(nearest["latitude"])
    )
    return origin, destination, round(float(distances.min()), 1)


def smoke_plan(
    data_root: Path,
    *,
    single_departure: bool = False,
    departure_time: str = DEPARTURE_TIME,
    departure_date: date = PINNED_WEDNESDAY,
) -> RunPlan:
    origin, destination, metres = smoke_endpoints(data_root)
    return RunPlan(
        slug=SINGLE_DEPARTURE_SLUG if single_departure else SLUG,
        modes=records.MODES,
        speed_walking_kmh=WALK_SPEED_KMH,
        departure=f"{departure_date.isoformat()}T{departure_time}",
        time_zone=TIME_ZONE,
        window_minutes=1 if single_departure else WINDOW_MINUTES,
        percentiles=PERCENTILES,
        max_time_minutes=MAX_TIME_MINUTES,
        origins=(origin,),
        destinations=(destination,),
        inputs=network_inputs(data_root),
        origins_description=f"spine center of tract {CITY_HALL_TRACT} (City Hall)",
        destinations_description=(
            f"nearest supermarket-format retailer to the origin ({metres} m straight-line)"
        ),
        note="EP-13 smoke route (ADR-0008 calendar; methodology.md travel model)",
    )


@dataclass
class SmokeReport:
    plan: RunPlan
    records: list[RunRecord] = field(default_factory=list)

    @property
    def outcomes(self) -> list[str]:
        return [r.outcome for r in self.records]

    @property
    def digests(self) -> list[str | None]:
        return records.outputs_agree([r.to_dict() for r in self.records])[1]

    @property
    def deterministic(self) -> bool:
        return records.outputs_agree([r.to_dict() for r in self.records])[0]

    @property
    def peak_rss_bytes(self) -> int:
        return max((r.rss.get("peak_rss_bytes", 0) for r in self.records), default=0)

    @property
    def under_kill_line(self) -> bool:
        return all(
            not r.rss.get("killed") and r.rss.get("peak_rss_bytes", 0) < KILL_BYTES
            for r in self.records
        )

    @property
    def ok(self) -> bool:
        return (
            bool(self.records)
            and all(o == records.COMPLETED for o in self.outcomes)
            and self.under_kill_line
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs": [r.run_id for r in self.records],
            "outcomes": self.outcomes,
            "canonical_value_digests": self.digests,
            "deterministic": self.deterministic,
            "peak_rss_bytes": self.peak_rss_bytes,
            "under_kill_line": self.under_kill_line,
            "wall_seconds": [r.wall_seconds for r in self.records],
        }


def run_smoke(
    data_root: Path,
    toolchain: Toolchain,
    *,
    repeats: int = REPEATS,
    single_departure: bool = False,
    departure_time: str = DEPARTURE_TIME,
    echo: Callable[[str], None] | None = None,
    runner: Callable[..., RunRecord] = harness.run,
) -> SmokeReport:
    """Run the smoke plan ``repeats`` times in a row, each run its own record."""
    say = echo or (lambda _line: None)
    plan = smoke_plan(data_root, single_departure=single_departure, departure_time=departure_time)
    say(
        f"smoke plan: {plan.origins_description} -> {plan.destinations_description}; "
        f"modes {', '.join(plan.modes)}; departure {plan.departure} {plan.time_zone}, "
        f"window {plan.window_minutes} min, percentiles {list(plan.percentiles)}, "
        f"max {plan.max_time_minutes} min, walk {plan.speed_walking_kmh} km/h"
    )
    report = SmokeReport(plan)
    for i in range(1, repeats + 1):
        say(f"smoke run {i} of {repeats}")
        record = runner(plan, data_root=data_root, toolchain=toolchain, echo=echo)
        report.records.append(record)
        if record.outcome != records.COMPLETED:
            say(f"smoke run {i}: {record.outcome}: {record.error}; stopping")
            break
    return report
