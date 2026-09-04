"""EP-15: the real pipeline's ``travel_times`` stage on crafted inputs and a scripted child
(no JVM): the packaged plan is the spike's two core runs verbatim; the stage routes them as
a night under runs/routing/, writes the matrix in the dictionary's shape and its report,
re-uses a finished night on the same plan, points, and inputs, resumes a stopped one,
refuses without the toolchain, and sits between ``network`` and ``metrics`` in the real
pipeline with the plan's parameters as its methods axis.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from phillysim.pipeline import real_pipeline
from phillysim.routing import stage as routing_stage
from phillysim.routing.matrix import MATRIX_COLUMNS, NIGHT_FILE, STOPPED, list_nights
from phillysim.routing.plan import DEFAULT_PLAN, PLANS_DIR, load_plan
from phillysim.routing.stage import (
    PLAN,
    TRAVEL_TIMES,
    TRAVEL_TIMES_REPORT,
    find_night,
    make_travel_times,
    stage_params,
    stage_plan,
)
from phillysim.routing.toolchain import Check, ToolchainReport
from phillysim.stages import Stage, StageContext, StageError
from test_matrix_driver import FAILING_CHILD, make_runner, roots  # noqa: F401


def test_the_stage_plan_is_the_spikes_core_runs_verbatim() -> None:
    plan = stage_plan()
    spike = load_plan(DEFAULT_PLAN)
    assert plan.source == PLAN and (PLANS_DIR / PLAN).is_file()
    assert plan.name == "travel-times"
    assert plan.core_runs == spike.core_runs == ("walk-48-wed", "transit-48-wed")
    assert [r.to_dict() for r in plan.runs] == [spike.run(n).to_dict() for n in spike.core_runs]
    for key in ("time_zone", "percentiles", "max_time_minutes", "snap_to_network"):
        assert getattr(plan, key) == getattr(spike, key)
    assert plan.origins == spike.origins and plan.destinations == spike.destinations
    assert plan.rehearsal_origins == spike.rehearsal_origins
    assert plan.core_wall_limit_hours == spike.core_wall_limit_hours == 8.0
    assert plan.dates == {"wednesday": "2026-09-23"}
    params = stage_params(plan)
    assert params["plan_sha256"] == plan.sha256 and params["origins_count"] == 408
    assert params["destinations_count"] == 1609 and len(params["runs"]) == 2
    json.dumps(params)  # JSON-serializable, as a stage parameter must be


def test_the_stage_is_registered_between_network_and_metrics() -> None:
    pipeline = real_pipeline()
    names = pipeline.names
    assert names.index("travel_times") == names.index("network") + 1
    assert names.index("metrics") == names.index("travel_times") + 1
    stage = pipeline["travel_times"]
    assert stage.inputs == (
        "curated/tracts_spine.parquet",
        "curated/snap_retailers.parquet",
        "intermediate/network",
        "intermediate/network.json",
    )
    assert stage.outputs == (TRAVEL_TIMES, TRAVEL_TIMES_REPORT)
    assert stage.params == stage_params()
    assert "Bucket B" in stage.description and "never published" in stage.description
    # The matrix's provenance runs back to the spine, the retailers, and both routing sources.
    raws = pipeline.upstream_raw(TRAVEL_TIMES)
    assert any("osm_network" in r for r in raws) and any("gtfs" in r for r in raws)
    assert any("snap_retailers" in r for r in raws) and any("cenpop" in r for r in raws)
    # publish does not read it: the public zone stays Bucket A until M5.
    assert TRAVEL_TIMES not in pipeline["publish"].inputs
    assert TRAVEL_TIMES not in pipeline["metrics"].inputs


# --- the body on crafted inputs --------------------------------------------------------------


def _accepting(_chain) -> ToolchainReport:
    return ToolchainReport(checks=(Check("test", True, "crafted record accepted"),))


def _refusing(_chain) -> ToolchainReport:
    return ToolchainReport(checks=(Check("jdk", False, "missing: .jdk (run install)"),))


class _Token:
    def check(self) -> None:
        pass


def _context(data_root: Path, body, params: dict | None = None) -> StageContext:
    stage = real_pipeline()["travel_times"]
    stage = Stage(
        stage.name,
        body,
        inputs=stage.inputs,
        outputs=stage.outputs,
        params={**stage.params, **(params or {})},
    )
    staging = data_root.parent / "staging"
    return StageContext(stage, data_root, staging, stage.params, cancel=_Token())


SMALL = {"origins_count": 8, "destinations_count": 5, "rehearsal_origins": []}


def test_the_stage_routes_a_night_and_writes_the_matrix_and_report(roots) -> None:  # noqa: F811
    data_root, chain = roots
    body = make_travel_times(toolchain=chain, runner=make_runner(), check=_accepting)
    ctx = _context(data_root, body, SMALL)
    body(ctx)
    matrix = pd.read_parquet(ctx.staging / TRAVEL_TIMES)
    assert list(matrix.columns) == list(MATRIX_COLUMNS)
    assert len(matrix) == 8 * 5 * 2 and set(matrix["mode"]) == {"walk", "walk_transit"}
    assert matrix.equals(
        matrix.sort_values(["origin_geoid", "site_id", "mode"]).reset_index(drop=True)
    )
    assert (matrix["time_median_min"] <= 120).all()
    report = json.loads((ctx.staging / TRAVEL_TIMES_REPORT).read_text("utf-8"))
    assert report["license_bucket"] == "B" and report["stage"] == "travel_times"
    assert report["night_id"].endswith("-travel-times") and not report["night_reused"]
    assert set(report["runs"]) == {"walk-48-wed", "transit-48-wed"}
    assert report["matrix"]["rows"] == 80 and report["matrix"]["modes"] == ["walk", "walk_transit"]
    assert report["plan"]["file"] == PLAN and len(report["plan"]["runs"]) == 2
    assert str(data_root) not in json.dumps(report)
    nights = list_nights(data_root)
    assert len(nights) == 1 and nights[0].name == report["night_id"]
    night = json.loads((nights[0] / NIGHT_FILE).read_text("utf-8"))
    assert night["state"] == "finished" and night["plan"]["name"] == "travel-times"
    assert (
        night["runs"]["walk-48-wed"]["matrix"]["canonical_value_sha256"]
        == (report["runs"]["walk-48-wed"]["matrix"]["canonical_value_sha256"])
    )
    # No probe file is left in staging beside the declared outputs.
    assert sorted(p.name for p in ctx.staging.rglob("*") if p.is_file()) == [
        "travel_times.json",
        "travel_times.parquet",
    ]


def test_a_second_run_reuses_the_finished_night_and_a_stopped_one_is_resumed(roots) -> None:  # noqa: F811
    data_root, chain = roots
    body = make_travel_times(toolchain=chain, runner=make_runner(), check=_accepting)
    body(_context(data_root, body, SMALL))
    first = list_nights(data_root)[0].name
    ctx = _context(data_root, body, SMALL)
    body(ctx)
    report = json.loads((ctx.staging / TRAVEL_TIMES_REPORT).read_text("utf-8"))
    assert report["night_reused"] is True and report["night_id"] == first
    assert len(list_nights(data_root)) == 1
    # A changed input (the clip's bytes) means a new night.
    (data_root / "intermediate" / "network" / "clip.osm.pbf").write_bytes(b"other" * 100)
    body(_context(data_root, body, SMALL))
    assert len(list_nights(data_root)) == 2
    # A stopped night (a failing transit child) is resumed by the next run, in place.
    failing = make_travel_times(
        toolchain=chain, runner=make_runner({"transit-48-wed": FAILING_CHILD}), check=_accepting
    )
    (data_root / "intermediate" / "network" / "clip.osm.pbf").write_bytes(b"third" * 100)
    with pytest.raises(StageError, match="ended stopped"):
        failing(_context(data_root, failing, SMALL))
    stopped = list_nights(data_root)[-1]
    assert json.loads((stopped / NIGHT_FILE).read_text("utf-8"))["state"] == STOPPED
    ctx = _context(data_root, body, SMALL)
    body(ctx)
    report = json.loads((ctx.staging / TRAVEL_TIMES_REPORT).read_text("utf-8"))
    assert report["night_resumed"] is True and report["night_id"] == stopped.name
    assert len(list_nights(data_root)) == 3
    resumed = json.loads((stopped / NIGHT_FILE).read_text("utf-8"))
    assert resumed["state"] == "finished" and resumed["runs"]["transit-48-wed"]["attempts"] == 2


def test_find_night_matches_plan_points_and_inputs(roots) -> None:  # noqa: F811
    data_root, chain = roots
    body = make_travel_times(toolchain=chain, runner=make_runner(), check=_accepting)
    body(_context(data_root, body, SMALL))
    night = json.loads((list_nights(data_root)[0] / NIGHT_FILE).read_text("utf-8"))
    plan = routing_stage._with_counts(stage_plan(), SMALL)
    record = json.loads(
        (list_nights(data_root)[0] / "walk-48-wed" / "record.json").read_text("utf-8")
    )
    digests = record["inputs"]
    assert find_night(
        data_root, plan, points_sha256=night["points"]["sha256"], input_digests=digests
    ) == (
        "reuse",
        night["night_id"],
    )
    assert find_night(data_root, plan, points_sha256="0" * 64, input_digests=digests) == (
        None,
        None,
    )
    other = {k: {**v, "sha256": "f" * 64} for k, v in digests.items()}
    assert find_night(
        data_root, plan, points_sha256=night["points"]["sha256"], input_digests=other
    ) == (
        None,
        None,
    )


def test_the_stage_refuses_without_the_toolchain_and_names_the_install(roots) -> None:  # noqa: F811
    data_root, chain = roots
    body = make_travel_times(toolchain=chain, runner=make_runner(), check=_refusing)
    with pytest.raises(StageError, match="toolchain install"):
        body(_context(data_root, body, SMALL))
    assert list_nights(data_root) == []


def test_the_stage_refuses_a_plan_whose_digest_moved(roots) -> None:  # noqa: F811
    data_root, chain = roots
    body = make_travel_times(toolchain=chain, runner=make_runner(), check=_accepting)
    with pytest.raises(StageError, match="packaged plan changed"):
        body(_context(data_root, body, {**SMALL, "plan_sha256": "0" * 64}))
