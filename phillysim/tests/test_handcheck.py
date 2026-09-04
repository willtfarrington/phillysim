"""EP-15: the hand check on crafted tables and a scripted child (no JVM): the ten pairs by
rule (every N-th tract, the nearest retailer, the farthest inside the censor for the fifth
and tenth, the substitution), the two single-departure runs and the forty checks, the tally
against a hand-typed planner file with the tolerance and the gate, and the CLI.
"""

from __future__ import annotations

import json

import geopandas as gpd
import pandas as pd
import pytest
from typer.testing import CliRunner

from phillysim.cli import app
from phillysim.routing import handcheck
from phillysim.routing.handcheck import (
    GATE,
    HANDCHECK_DIR,
    HANDCHECK_FILE,
    PLANNER_FILE,
    RULE_FARTHEST,
    RULE_NEAREST,
    apply_planner,
    handcheck_lines,
    handcheck_plans,
    pick_origins,
    planner_template,
    run_handcheck,
    select_pairs,
    tally,
    tolerance_minutes,
)
from phillysim.routing.matrix import run_matrix
from phillysim.spine import NAD83
from test_matrix_driver import make_runner, roots, small_plan  # noqa: F401

runner_cli = CliRunner()


def test_pick_origins_takes_every_nth_from_the_first_and_substitutes_forward() -> None:
    geoids = [f"g{i:02d}" for i in range(12)]
    picks = pick_origins(reversed(geoids), every=3, count=10)
    assert [p["geoid"] for p in picks] == ["g00", "g03", "g06", "g09"]
    assert [p["position"] for p in picks] == [1, 2, 3, 4]
    assert all(p["substituted_for"] is None for p in picks)
    picks = pick_origins(geoids, every=3, count=2, skip={"g03", "g04"})
    assert [p["geoid"] for p in picks] == ["g00", "g05"]
    assert picks[1]["substituted_for"] == "g03" and picks[1]["rule_index"] == 3
    picks = pick_origins(geoids, every=1, count=3, skip={"g01"})
    assert [p["geoid"] for p in picks] == ["g00", "g02", "g03"]
    with pytest.raises(ValueError, match="no substitute"):
        pick_origins(["a", "b"], every=1, count=2, skip={"b"})


def _tables() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame]:
    geoids = [f"4210100{i:04d}" for i in range(12)]
    lons = [-75.10 - i * 0.01 for i in range(12)]
    lats = [39.90 + i * 0.01 for i in range(12)]
    spine = gpd.GeoDataFrame(
        {
            "geoid": geoids,
            "name": [f"Tract {i}" for i in range(12)],
            "centroid_lon": lons,
            "centroid_lat": lats,
        },
        geometry=gpd.points_from_xy(lons, lats),
        crs=NAD83,
    ).to_crs("EPSG:26918")
    site_lons = [-75.10, -75.12, -75.15, -75.18]
    site_lats = [39.90, 39.92, 39.95, 39.98]
    retailers = gpd.GeoDataFrame(
        {
            "site_id": [f"snap_retailers:{i}" for i in range(4)],
            "name": ["A", "B", "C", "D"],
            "supermarket_format": [True, True, False, True],
            "longitude": site_lons,
            "latitude": site_lats,
        },
        geometry=gpd.points_from_xy(site_lons, site_lats),
        crs="EPSG:4326",
    ).to_crs("EPSG:26918")
    rows = []
    for g in geoids:
        for s in range(4):
            minutes = float((int(g[-2:]) * 9 + s * 31) % 130)
            rows.append(
                {
                    "origin_geoid": g,
                    "site_id": f"snap_retailers:{s}",
                    "mode": "walk",
                    "time_median_min": min(minutes, 120.0),
                    "time_p85_min": min(minutes, 120.0),
                }
            )
    return spine, retailers, pd.DataFrame(rows)


def test_select_pairs_applies_the_nearest_and_farthest_rules() -> None:
    spine, retailers, walk = _tables()
    pairs = select_pairs(spine, retailers, walk, max_time=120, every=1, count=10, long_tail=(5, 10))
    assert [p["position"] for p in pairs] == list(range(1, 11))
    assert [p["origin_geoid"] for p in pairs] == sorted(spine["geoid"])[:10]
    for p in pairs:
        assert p["site_id"] != "snap_retailers:2", "never a non-supermarket retailer"
        assert (
            p["origin_lon"]
            == spine.loc[spine["geoid"] == p["origin_geoid"], "centroid_lon"].iloc[0]
        )
        assert p["straight_line_m"] >= 0 and p["site_name"]
        if p["position"] in (5, 10):
            assert p["rule"] == RULE_FARTHEST
            candidates = walk[
                (walk["origin_geoid"] == p["origin_geoid"])
                & (walk["site_id"] != "snap_retailers:2")
            ]
            finite = candidates[candidates["time_median_min"] < 120]
            assert p["core_walk_typical_min"] == finite["time_median_min"].max()
        else:
            assert p["rule"] == RULE_NEAREST
            centre = spine.loc[spine["geoid"] == p["origin_geoid"]].geometry.iloc[0]
            supermarkets = retailers[retailers["supermarket_format"]]
            nearest = supermarkets.loc[supermarkets.distance(centre).idxmin(), "site_id"]
            assert p["site_id"] == nearest
    # A skipped tract is substituted by the next in sorted order, and it is recorded.
    skipped = select_pairs(
        spine, retailers, walk, max_time=120, every=1, count=2, skip={sorted(spine["geoid"])[1]}
    )
    assert skipped[1]["origin_geoid"] == sorted(spine["geoid"])[2]
    assert skipped[1]["substituted_for"] == sorted(spine["geoid"])[1]


def test_handcheck_plans_are_single_departure_both_modes_at_the_two_times() -> None:
    spine, retailers, walk = _tables()
    pairs = select_pairs(spine, retailers, walk, max_time=120, every=1, count=10)
    plans_ = handcheck_plans(pairs, small_plan(), {"osm": "intermediate/network/clip.osm.pbf"})
    assert [p.slug for p in plans_] == ["handcheck-0830", "handcheck-1730"]
    for p in plans_:
        assert p.modes == ("walk", "walk_transit") and p.window_minutes == 1
        assert p.departure.startswith("2026-09-23T") and p.time_zone == "America/New_York"
        assert p.speed_walking_kmh == 4.8 and p.max_time_minutes == 120 and p.snap_to_network
        assert len(p.origins) == 10 and len(p.destinations) == len({x["site_id"] for x in pairs})
    assert plans_[0].departure.endswith("08:30") and plans_[1].departure.endswith("17:30")


# --- the runs on a scripted child --------------------------------------------------------


@pytest.fixture
def night_with_tables(roots):  # noqa: F811 - the imported fixture
    """A finished small night whose crafted tables also carry what the hand check needs."""
    data_root, chain = roots
    spine = pd.read_parquet(data_root / "curated" / "tracts_spine.parquet")
    gpd.GeoDataFrame(
        spine.assign(name=[f"Tract {g}" for g in spine["geoid"]]),
        geometry=gpd.points_from_xy(spine["centroid_lon"], spine["centroid_lat"]),
        crs=NAD83,
    ).to_crs("EPSG:26918").to_parquet(data_root / "curated" / "tracts_spine.parquet")
    retailers = pd.read_parquet(data_root / "curated" / "snap_retailers.parquet")
    gpd.GeoDataFrame(
        retailers.assign(
            name=[f"Store {i}" for i in range(len(retailers))],
            supermarket_format=[True, False, True, True, True],
        ),
        geometry=gpd.points_from_xy(retailers["longitude"], retailers["latitude"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:26918").to_parquet(data_root / "curated" / "snap_retailers.parquet")
    plan = small_plan()
    night = run_matrix(plan, data_root=data_root, toolchain=chain, runner=make_runner())
    return data_root, chain, night


def test_run_handcheck_routes_forty_checks_and_leaves_the_tally_pending(night_with_tables) -> None:
    data_root, chain, night = night_with_tables
    report = run_handcheck(
        night.dir,
        data_root=data_root,
        toolchain=chain,
        runner=make_runner(),
        every=1,
        count=8,
        plan=small_plan(),
    )
    assert len(report["pairs"]) == 8 and len(report["checks"]) == 8 * 2 * 2
    assert report["departure_times"] == ["08:30", "17:30"] and report["date"] == "2026-09-23"
    assert set(report["runs"]) == {"08:30", "17:30"}
    assert (night.dir / HANDCHECK_DIR / "handcheck-0830" / "record.json").is_file()
    assert (night.dir / HANDCHECK_DIR / "handcheck-1730" / "travel_times.csv").is_file()
    assert report["tally"] == {"checks": 32, "within": None}
    ids = [c["check_id"] for c in report["checks"]]
    assert (
        ids[0] == "01-0830-walk"
        and ids[1] == "01-0830-walk_transit"
        and ids[-1] == "08-1730-walk_transit"
    )
    assert len(set(ids)) == len(ids)
    for check in report["checks"]:
        assert check["censored"] == (check["project_minutes"] is None)
        if not check["censored"]:
            assert 0 <= check["project_minutes"] < 120
    written = json.loads((night.dir / HANDCHECK_DIR / HANDCHECK_FILE).read_text("utf-8"))
    assert written["checks"] == report["checks"]
    assert str(data_root) not in json.dumps(written)
    lines = handcheck_lines(report)
    assert lines[0].startswith(f"hand check for night {night.id}: 8 pairs, 32 checks")
    assert any(line.startswith("tally: pending") for line in lines)
    template = planner_template(report)
    assert template.splitlines()[0] == "check_id,planner_minutes"
    assert len(template.splitlines()) == 33
    # A second run keeps the earlier one aside.
    run_handcheck(
        night.dir,
        data_root=data_root,
        toolchain=chain,
        runner=make_runner(),
        every=1,
        count=8,
        plan=small_plan(),
    )
    assert len([p for p in (night.dir / HANDCHECK_DIR).glob("handcheck-0830*")]) == 2


# --- the tally ----------------------------------------------------------------------------------


def test_tolerance_is_the_larger_of_minutes_and_share() -> None:
    assert tolerance_minutes("walk", 10) == 3.0
    assert tolerance_minutes("walk", 40) == 6.0
    assert tolerance_minutes("walk_transit", 20) == 10.0
    assert tolerance_minutes("walk_transit", 60) == 15.0


def _report(checks: list[tuple[str, str, float | None]]) -> dict:
    return {
        "max_time_minutes": 120,
        "gate": list(GATE),
        "checks": [
            {"check_id": i, "mode": m, "project_minutes": p, "censored": p is None}
            for i, m, p in checks
        ],
    }


def test_tally_applies_the_tolerance_and_counts_no_answers_as_out() -> None:
    report = _report(
        [
            ("01-walk", "walk", 10.0),  # planner 12: within 3 min
            ("02-walk", "walk", 50.0),  # planner 40: 10 off, tolerance 6 -> out
            ("03-transit", "walk_transit", 30.0),  # planner 38: within 10
            ("04-transit", "walk_transit", 80.0),  # planner 60: 20 off, tolerance 15 -> out
            ("05-walk", "walk", 20.0),  # no answer -> out
            ("06-walk", "walk", None),  # censored, planner 130: both over -> within
            ("07-walk", "walk", None),  # censored, planner 90 -> out
        ]
    )
    planner = {
        "01-walk": 12.0,
        "02-walk": 40.0,
        "03-transit": 38.0,
        "04-transit": 60.0,
        "06-walk": 130.0,
        "07-walk": 90.0,
    }
    out = tally(report, planner)
    assert out["checks"] == 7 and out["within"] == 3 and out["no_answer"] == 1
    assert out["gate"] == [32, 40] and out["gate_met"] is False
    rows = {r["check_id"]: r for r in out["rows"]}
    assert rows["01-walk"]["within"] and rows["01-walk"]["difference_minutes"] == -2.0
    assert not rows["02-walk"]["within"] and rows["02-walk"]["tolerance_minutes"] == 6.0
    assert rows["03-transit"]["within"] and not rows["04-transit"]["within"]
    assert rows["05-walk"]["note"] == "no planner answer"
    assert rows["06-walk"]["within"] and "both at or over" in rows["06-walk"]["note"]
    assert not rows["07-walk"]["within"] and "censored" in rows["07-walk"]["note"]
    assert out["by_mode"]["walk"] == {"checks": 5, "within": 2}
    assert out["by_mode"]["walk_transit"] == {"checks": 2, "within": 1}
    forty = _report([(f"{i:02d}-walk", "walk", 10.0) for i in range(40)])
    full = tally(forty, {f"{i:02d}-walk": 10.0 for i in range(40)})
    assert full["within"] == 40 and full["gate_met"] is True
    assert tally(forty, {f"{i:02d}-walk": 10.0 for i in range(31)})["gate_met"] is False


def test_apply_planner_reads_the_hand_typed_file_and_writes_the_tally(night_with_tables) -> None:
    data_root, chain, night = night_with_tables
    report = run_handcheck(
        night.dir,
        data_root=data_root,
        toolchain=chain,
        runner=make_runner(),
        every=1,
        count=8,
        plan=small_plan(),
    )
    directory = night.dir / HANDCHECK_DIR
    lines = ["check_id,planner_minutes"]
    for check in report["checks"]:
        minutes = "" if check["project_minutes"] is None else f"{check['project_minutes'] + 1:.0f}"
        lines.append(f"{check['check_id']},{minutes}")
    (directory / PLANNER_FILE).write_text("\n".join(lines) + "\n", "utf-8")
    updated = apply_planner(night.dir)
    assert updated["tally"]["checks"] == 32
    censored = sum(1 for c in report["checks"] if c["censored"])
    assert updated["tally"]["within"] == 32 - censored
    assert updated["tally"]["no_answer"] == censored
    written = json.loads((directory / HANDCHECK_FILE).read_text("utf-8"))
    assert written["tally"]["within"] == updated["tally"]["within"]
    assert any("tally:" in line and "within tolerance" in line for line in handcheck_lines(updated))
    # A file elsewhere, with a BOM and a stray non-number, still reads.
    other = data_root / "planner-other.csv"
    other.write_text("﻿check_id,planner_minutes\n01-0830-walk,7\n01-0830-walk_transit,x\n", "utf-8")
    assert handcheck.read_planner_file(other) == {"01-0830-walk": 7.0, "01-0830-walk_transit": None}


def test_route_handcheck_cli_tally_and_template(night_with_tables) -> None:
    data_root, chain, night = night_with_tables
    run_handcheck(
        night.dir,
        data_root=data_root,
        toolchain=chain,
        runner=make_runner(),
        every=1,
        count=8,
        plan=small_plan(),
    )
    result = runner_cli.invoke(
        app,
        ["route", "handcheck", "--data-root", str(data_root), "--night", night.id, "--template"],
    )
    assert result.exit_code == 0 and result.output.startswith("check_id,planner_minutes\n")
    planner = data_root / "planner.csv"
    planner.write_text(result.output, "utf-8")  # every answer blank: nothing within
    result = runner_cli.invoke(
        app,
        [
            "route",
            "handcheck",
            "--data-root",
            str(data_root),
            "--night",
            night.id,
            "--planner",
            str(planner),
        ],
    )
    assert result.exit_code == 1 and "0 of 32 within tolerance" in result.output
    result = runner_cli.invoke(app, ["route", "handcheck", "--help"])
    assert result.exit_code == 0 and "--planner" in result.output and "--skip" in result.output
    result = runner_cli.invoke(
        app, ["route", "handcheck", "--data-root", str(data_root / "none"), "--template"]
    )
    assert result.exit_code == 1 and "FAIL no night" in result.output
