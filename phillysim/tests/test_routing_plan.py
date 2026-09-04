"""EP-14: the matrix plan file. The packaged ``m3-spike.json`` parses, every parameter equals
ADR-0008's and methodology.md's, the run list is the brief's table with the core runs first,
and the plan carries names and parameters only, no path. Plus the loader's rules, the
points built from the curated tables (on crafted tables), the feed-window check on crafted
feed zips, and the harness plan one run becomes. No JVM, no data root beyond ``tmp_path``.
"""

from __future__ import annotations

import copy
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from phillysim.routing import plan as plans
from phillysim.routing import records
from phillysim.routing.plan import (
    DEFAULT_PLAN,
    PLANS_DIR,
    MatrixPlan,
    PlanError,
    build_points,
    check_feed_windows,
    feed_window,
    feed_windows,
    load_plan,
    origin_order,
    parse_plan,
    plan_path,
    points_of,
    read_points,
    run_plan,
    write_points,
)
from phillysim.routing.records import RunPlan

SAMPLE_TRACTS = (
    "42101000101",
    "42101000102",
    "42101000200",
    "42101000300",
    "42101000401",
    "42101000403",
)

# --- the packaged plan against ADR-0008 ---------------------------------------------------


@pytest.fixture(scope="module")
def spike() -> MatrixPlan:
    return load_plan(DEFAULT_PLAN)


def test_the_packaged_plans_are_the_spike_and_the_stages() -> None:
    """EP-15: ``travel-times.json`` (the stage's plan) sits beside ``m3-spike.json``; its
    content is pinned against the spike's core runs in ``test_travel_times_stage.py``."""
    assert sorted(p.name for p in PLANS_DIR.glob("*.json")) == [
        "m3-spike.json",
        "travel-times.json",
    ]
    for name in ("m3-spike.json", "travel-times.json"):
        plan = load_plan(name)
        assert plan.core_runs == ("walk-48-wed", "transit-48-wed")
        assert plan.core_wall_limit_hours == 8.0 and plan.max_time_minutes == 120


def test_the_plan_file_is_packaged_and_resolves_by_name_or_path(spike: MatrixPlan) -> None:
    assert plan_path(DEFAULT_PLAN) == PLANS_DIR / DEFAULT_PLAN
    assert plan_path(PLANS_DIR / DEFAULT_PLAN) == PLANS_DIR / DEFAULT_PLAN
    assert spike.source == DEFAULT_PLAN and len(spike.sha256) == 64
    with pytest.raises(PlanError, match="no plan file"):
        plan_path("no-such-plan.json")


def test_the_plan_parameters_equal_adr_0008(spike: MatrixPlan) -> None:
    assert spike.name == "m3-spike"
    assert spike.time_zone == "America/New_York"
    assert spike.dates == {"wednesday": "2026-09-23", "saturday": "2026-09-26"}
    assert spike.percentiles == (50, 85)
    assert spike.max_time_minutes == 120  # the censor
    assert spike.snap_to_network is True
    assert spike.core_wall_limit_hours == 8 and spike.core_wall_limit_seconds == 28_800
    assert spike.origins.table == "tracts_spine" and spike.origins.count == 408
    assert (spike.origins.id, spike.origins.lon, spike.origins.lat) == (
        "geoid",
        "centroid_lon",
        "centroid_lat",
    )
    assert spike.destinations.table == "snap_retailers" and spike.destinations.count == 1609
    assert (spike.destinations.id, spike.destinations.lon, spike.destinations.lat) == (
        "site_id",
        "longitude",
        "latitude",
    )
    assert spike.rehearsal_origins == SAMPLE_TRACTS  # the CI samples' GEOIDs
    assert spike.origins.path == "curated/tracts_spine.parquet"
    assert spike.destinations.path == "curated/snap_retailers.parquet"


def test_the_run_list_is_the_briefs_table_with_the_core_runs_first(spike: MatrixPlan) -> None:
    rows = [
        (r.name, r.mode, r.speed_walking_kmh, r.date, r.departure_time, r.window_minutes, r.role)
        for r in spike.runs
    ]
    assert rows == [
        ("walk-48-wed", "walk", 4.8, "2026-09-23", "08:00", 1, "core"),
        ("transit-48-wed", "walk_transit", 4.8, "2026-09-23", "08:00", 720, "core"),
        ("walk-48-wed-repeat", "walk", 4.8, "2026-09-23", "08:00", 1, "repeat"),
        ("transit-48-wed-repeat", "walk_transit", 4.8, "2026-09-23", "08:00", 720, "repeat"),
        ("walk-30-wed", "walk", 3.0, "2026-09-23", "08:00", 1, "sensitivity"),
        ("transit-30-wed", "walk_transit", 3.0, "2026-09-23", "08:00", 720, "sensitivity"),
        ("transit-48-sat", "walk_transit", 4.8, "2026-09-26", "08:00", 720, "saturday"),
    ]
    assert spike.core_runs == ("walk-48-wed", "transit-48-wed") == spike.run_names[:2]
    assert spike.run("walk-48-wed-repeat").repeat_of == "walk-48-wed"
    assert spike.run("transit-48-wed-repeat").repeat_of == "transit-48-wed"
    # One departure per minute over 08:00-20:00 = 720 departures; a walk run is time-invariant.
    for run in spike.runs:
        assert run.departures == run.window_minutes
        assert run.departures == (720 if run.mode == "walk_transit" else 1)
        assert run.departure == f"{run.date}T08:00"
    # Every transit date is a pinned date and a real Wednesday / Saturday.
    assert pd.Timestamp("2026-09-23").day_name() == "Wednesday"
    assert pd.Timestamp("2026-09-26").day_name() == "Saturday"


def test_the_plan_carries_no_path(spike: MatrixPlan) -> None:
    raw = json.loads((PLANS_DIR / DEFAULT_PLAN).read_text("utf-8"))

    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for k, v in value.items():
                yield k
                yield from strings(v)
        elif isinstance(value, list):
            for v in value:
                yield from strings(v)

    for text in strings(raw):
        assert records.is_data_root_relative(text), text
        assert "\\" not in text and not text.startswith("data/"), text
    assert "path" not in raw and "path" not in raw["origins"] and "path" not in raw["destinations"]
    assert spike.extra == {}  # every key is one the loader knows
    assert spike.to_dict()["runs"][0] == {
        "name": "walk-48-wed",
        "mode": "walk",
        "speed_walking_kmh": 4.8,
        "date": "2026-09-23",
        "departure_time": "08:00",
        "window_minutes": 1,
        "role": "core",
    }


def test_describe_names_every_parameter(spike: MatrixPlan) -> None:
    text = plans.describe(spike.run("transit-48-sat"))
    assert "walk_transit at 4.8 km/h" in text and "Sat 2026-09-26 08:00" in text
    assert "720 departure(s)" in text and "saturday" in text


# --- the loader's rules ---------------------------------------------------------------------


def _mutated(mutate) -> dict:
    raw = json.loads((PLANS_DIR / DEFAULT_PLAN).read_text("utf-8"))
    mutate(raw)
    return raw


def _set_run(raw: dict, name: str, **fields) -> None:
    for run in raw["runs"]:
        if run["name"] == name:
            run.update(fields)


def _rename(raw: dict, name: str, new_name: str) -> None:
    for run in raw["runs"]:
        if run["name"] == name:
            run["name"] = new_name


def _move_first(raw: dict, name: str) -> None:
    run = next(r for r in raw["runs"] if r["name"] == name)
    raw["runs"].remove(run)
    raw["runs"].insert(0, run)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda r: r.update(schema_version=2), "schema_version"),
        (lambda r: _set_run(r, "walk-48-wed-repeat", speed_walking_kmh=3.0), "parameters differ"),
        (lambda r: _move_first(r, "walk-30-wed"), "core runs must come first"),
        (lambda r: _set_run(r, "walk-30-wed", mode="bike"), "mode must be one of"),
        (lambda r: _set_run(r, "walk-30-wed", date="2026-13-01"), "not an ISO date"),
        (lambda r: _set_run(r, "walk-30-wed", date="2026-09-30"), "not one of the plan's dates"),
        (lambda r: _rename(r, "walk-30-wed", "walk-48-wed"), "run names repeat"),
        (lambda r: _set_run(r, "walk-30-wed", departure_time="8:00"), "HH:MM"),
        (lambda r: _set_run(r, "walk-30-wed", window_minutes=0), "window_minutes"),
        (lambda r: _set_run(r, "walk-30-wed", role="extra"), "role must be one of"),
        (lambda r: _set_run(r, "walk-30-wed", repeat_of="walk-48-wed"), "go together"),
        (lambda r: _set_run(r, "walk-48-wed-repeat", repeat_of="transit-48-sat"), "earlier run"),
        (lambda r: r["origins"].update(table="tract_metrics"), "unknown table"),
        (lambda r: r.update(core_runs=["nope"]), "core_runs must name runs"),
        (lambda r: r.update(core_wall_limit_hours=0), "core_wall_limit_hours"),
        (lambda r: r.update(percentiles=[0, 50]), "percentiles"),
        (lambda r: r.update(snap_to_network="yes"), "snap_to_network"),
        (lambda r: r.pop("rehearsal_origins"), "lacks 'rehearsal_origins'"),
        (lambda r: r.update(rehearsal_origins=["a", "a"]), "repeat an ID"),
        (lambda r: r.update(runs=[]), "at least one run"),
    ],
)
def test_the_loader_refuses_a_bad_plan(mutate, message: str) -> None:
    with pytest.raises(PlanError, match=message):
        parse_plan(_mutated(mutate))


def test_load_plan_refuses_non_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{", "utf-8")
    with pytest.raises(PlanError, match="not JSON"):
        load_plan(bad)


# --- the points -------------------------------------------------------------------------------


def _tables(data_root: Path, *, n_origins: int = 8, n_destinations: int = 5) -> None:
    (data_root / "curated").mkdir(parents=True)
    geoids = [f"4210100{i:04d}" for i in range(n_origins)]
    pd.DataFrame(
        {
            "geoid": geoids,
            "name": [f"Tract {g}" for g in geoids],
            "centroid_lon": [-75.1 - i * 0.01 for i in range(n_origins)],
            "centroid_lat": [39.9 + i * 0.01 for i in range(n_origins)],
        }
    ).to_parquet(data_root / "curated" / "tracts_spine.parquet", index=False)
    pd.DataFrame(
        {
            "site_id": [f"snap_retailers:10000{i}" for i in range(n_destinations)],
            "longitude": [-75.2 + i * 0.01 for i in range(n_destinations)],
            "latitude": [39.95 - i * 0.01 for i in range(n_destinations)],
            "supermarket_format": [i % 2 == 0 for i in range(n_destinations)],
        }
    ).to_parquet(data_root / "curated" / "snap_retailers.parquet", index=False)


def small_plan(**overrides) -> MatrixPlan:
    raw = json.loads((PLANS_DIR / DEFAULT_PLAN).read_text("utf-8"))
    raw["name"] = "test-plan"
    raw["origins"]["count"] = 8
    raw["destinations"]["count"] = 5
    raw["rehearsal_origins"] = ["42101000005", "42101000002", "42101000007"]
    raw.update(overrides)
    return parse_plan(raw, source="test-plan.json", sha256="0" * 64)


def test_origin_order_puts_the_rehearsal_first_then_sorted() -> None:
    assert origin_order(["c", "a", "b", "d"], ["d", "b"]) == ["d", "b", "a", "c"]
    with pytest.raises(PlanError, match="rehearsal origins not in"):
        origin_order(["a"], ["z"])


def test_build_points_reads_the_curated_tables_once(tmp_path: Path) -> None:
    _tables(tmp_path)
    plan = small_plan()
    points = build_points(tmp_path, plan)
    assert list(points.columns) == ["role", "id", "lon", "lat"]
    origins = points[points["role"] == "origin"]
    assert list(origins["id"])[:3] == ["42101000005", "42101000002", "42101000007"]
    assert list(origins["id"])[3:] == sorted(set(origins["id"]) - set(plan.rehearsal_origins))
    assert (points["role"] == "destination").sum() == 5
    subset = build_points(tmp_path, plan, origins_subset=3)
    assert list(subset.loc[subset["role"] == "origin", "id"]) == list(plan.rehearsal_origins)
    assert (subset["role"] == "destination").sum() == 5  # always every destination
    with pytest.raises(PlanError, match="--origins-subset must be in 1..8"):
        build_points(tmp_path, plan, origins_subset=9)
    write_points(subset, tmp_path / "points.parquet")
    back = read_points(tmp_path / "points.parquet")
    pd.testing.assert_frame_equal(back, subset)
    o = points_of(back, "origin")
    assert o[0].id == "42101000005" and isinstance(o[0].lon, float)


def test_build_points_refuses_a_table_that_does_not_match_the_plan(tmp_path: Path) -> None:
    _tables(tmp_path, n_origins=7)
    with pytest.raises(PlanError, match="has 7 rows, the plan says 8"):
        build_points(tmp_path, small_plan())
    with pytest.raises(FileNotFoundError, match="missing"):
        build_points(tmp_path / "nowhere", small_plan())
    _tables(tmp_path / "dup")
    frame = pd.read_parquet(tmp_path / "dup" / "curated" / "tracts_spine.parquet")
    frame.loc[1, "geoid"] = frame.loc[0, "geoid"]
    frame.to_parquet(tmp_path / "dup" / "curated" / "tracts_spine.parquet", index=False)
    with pytest.raises(PlanError, match="not unique"):
        build_points(tmp_path / "dup", small_plan())


# --- the feeds' windows -----------------------------------------------------------------------


def feed_zip(path: Path, start: str | None, end: str | None, version: str = "v1") -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as feed:
        feed.writestr("agency.txt", "agency_id,agency_name\nSEPTA,SEPTA\n")
        if start is not None:
            feed.writestr(
                "feed_info.txt",
                "feed_publisher_name,feed_start_date,feed_end_date,feed_version\n"
                f"SEPTA,{start},{end},{version}\n",
            )
    path.write_bytes(buffer.getvalue())
    return path


def test_feed_window_reads_feed_info_dates_as_iso(tmp_path: Path) -> None:
    assert feed_window(feed_zip(tmp_path / "bus.zip", "20260906", "20270220", "Fall")) == {
        "feed_start_date": "2026-09-06",
        "feed_end_date": "2027-02-20",
        "feed_version": "Fall",
    }
    assert feed_window(feed_zip(tmp_path / "none.zip", None, None))["feed_start_date"] is None


def test_check_feed_windows_refuses_dates_outside_either_feed(tmp_path: Path) -> None:
    (tmp_path / "intermediate" / "network").mkdir(parents=True)
    inputs = {
        "osm": "intermediate/network/clip.osm.pbf",
        "gtfs_bus": "intermediate/network/google_bus.zip",
        "gtfs_rail": "intermediate/network/google_rail.zip",
    }
    feed_zip(tmp_path / inputs["gtfs_bus"], "20260906", "20270220")
    feed_zip(tmp_path / inputs["gtfs_rail"], "20260906", "20261017")
    windows = feed_windows(tmp_path, inputs)
    assert set(windows) == {"gtfs_bus", "gtfs_rail"}  # the osm input is not a feed
    assert check_feed_windows(load_plan(DEFAULT_PLAN), windows) == []
    feed_zip(tmp_path / inputs["gtfs_rail"], "20260906", "20260920")  # ends before the dates
    problems = check_feed_windows(load_plan(DEFAULT_PLAN), feed_windows(tmp_path, inputs))
    assert problems == [
        "gtfs_rail: 2026-09-23 is outside the feed's window 2026-09-06..2026-09-20",
        "gtfs_rail: 2026-09-26 is outside the feed's window 2026-09-06..2026-09-20",
    ]
    feed_zip(tmp_path / inputs["gtfs_rail"], None, None)
    problems = check_feed_windows(load_plan(DEFAULT_PLAN), feed_windows(tmp_path, inputs))
    assert problems == ["gtfs_rail: feed_info.txt carries no authoritative window"]


# --- one run as a harness plan --------------------------------------------------------------


def test_run_plan_carries_the_runs_parameters_and_the_points(tmp_path: Path) -> None:
    _tables(tmp_path)
    plan = small_plan()
    points = build_points(tmp_path, plan, origins_subset=3)
    inputs = {"osm": "intermediate/network/clip.osm.pbf", "gtfs_bus": "intermediate/network/b.zip"}
    harness_plan = run_plan(plan, plan.run("transit-30-wed"), points, inputs, origins_subset=3)
    assert isinstance(harness_plan, RunPlan)
    assert harness_plan.slug == "transit-30-wed" and harness_plan.modes == ("walk_transit",)
    assert harness_plan.speed_walking_kmh == 3.0
    assert harness_plan.departure == "2026-09-23T08:00" and harness_plan.window_minutes == 720
    assert harness_plan.time_zone == "America/New_York"
    assert harness_plan.percentiles == (50, 85) and harness_plan.max_time_minutes == 120
    assert harness_plan.snap_to_network is True
    assert len(harness_plan.origins) == 3 and len(harness_plan.destinations) == 5
    assert harness_plan.inputs == inputs
    assert "rehearsal subset of 3" in harness_plan.origins_description
    assert "720 departure(s)" in harness_plan.note and "sensitivity" in harness_plan.note
    walk = run_plan(plan, plan.run("walk-48-wed-repeat"), points, inputs)
    assert walk.modes == ("walk",) and walk.window_minutes == 1 and "of walk-48-wed" in walk.note
    # The harness plan round-trips with snap_to_network; an EP-13 plan without it reads False.
    back = RunPlan.from_dict(json.loads(json.dumps(harness_plan.to_dict())))
    assert back == harness_plan
    legacy = copy.deepcopy(harness_plan.to_dict())
    del legacy["snap_to_network"]
    assert RunPlan.from_dict(legacy).snap_to_network is False
