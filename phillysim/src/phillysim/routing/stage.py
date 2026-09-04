"""The real pipeline's ``travel_times`` stage (EP-15, registered on the go verdict).

architecture.md's stage 9: the travel-time matrices. The body is the matrix
driver (:mod:`~phillysim.routing.matrix`) on the two **core runs** of the M3
spike, written down as the tracked plan ``plans/travel-times.json`` (the
core runs of ``m3-spike.json``, verbatim: walk at 4.8 km/h, and walk+transit
at 4.8 km/h over the pinned Wednesday's 08:00–20:00 window at one departure
per minute; percentiles 50 and 85; censored at 120 minutes), executed as a
**night** under ``<data root>/runs/routing/<UTC stamp>-travel-times/`` with
every record of EP-13 and EP-14, and then the two matrices concatenated into
``curated/travel_times.parquet`` in the data dictionary's shape (one row per
origin × destination × mode, sorted by key), **Bucket B by derivation** from
the clipped OSM network (ADR-0003). ``intermediate/travel_times.json`` holds
the night's ID, each run's wall, peak RSS, digests, and sanity counts, and the
matrix's digests, so a checkpoint can compare the stage's output with the
spike's night pair by digest without re-routing.

The stage's fingerprint covers the spine, the retailer layer, the routing
inputs (``intermediate/network/`` and its report), and the plan's parameters
(the file's digest and every run's parameters), so a controlled refresh of a
source, a new clip, or a parameter change re-runs routing: an unattended
run of about a quarter of an hour on the development machine (EP-14's
night), not a build step. A fresh clone's ``phillysim run`` therefore needs
the routing group and the toolchain installed first (``uv sync --locked
--group routing``, ``phillysim toolchain install``); the stage refuses with
those instructions otherwise, and CI never reaches it (the real pipeline is
not run in CI).

**Resume and re-use.** Before routing, the stage looks under ``runs/routing/``
for the latest night of this plan whose points table has the same digest and
whose completed core runs recorded the same input digests: a ``finished``
one is re-used (no routing; a stage that failed after its night, or a night
launched by hand with ``route matrix --plan travel-times.json``, is adopted),
a ``stopped`` one is resumed. The driver never imports r5py; the JVM runs in
the harness child.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from phillysim.network import NETWORK_DIR, NETWORK_REPORT
from phillysim.routing import harness, records
from phillysim.routing.matrix import (
    FINISHED,
    MATRIX_COLUMNS,
    MATRIX_FILE,
    MATRIX_KEY,
    STOPPED,
    Night,
    list_nights,
    run_matrix,
    write_matrix,
)
from phillysim.routing.plan import (
    POINTS_FILE,
    MatrixPlan,
    build_points,
    load_plan,
    write_points,
)
from phillysim.routing.records import COMPLETED, RunRecord
from phillysim.routing.toolchain import Toolchain, ToolchainReport
from phillysim.routing.toolchain import check as toolchain_check
from phillysim.stages import StageContext, StageError

TRAVEL_TIMES = "curated/travel_times.parquet"
TRAVEL_TIMES_REPORT = "intermediate/travel_times.json"
PLAN = "travel-times.json"
LICENSE_BUCKET = "B"
STAGE_NAME = "travel_times"
log = logging.getLogger("phillysim.routing")


def stage_plan() -> MatrixPlan:
    return load_plan(PLAN)


def stage_params(plan: MatrixPlan | None = None) -> dict[str, Any]:
    """The stage's parameters (the methods axis, ADR-0006): the plan file, its digest, and
    every run's parameters verbatim, plus the table sizes the plan expects (overridable
    for the samples)."""
    plan = plan or stage_plan()
    return {
        "plan": plan.source,
        "plan_sha256": plan.sha256,
        "time_zone": plan.time_zone,
        "percentiles": list(plan.percentiles),
        "max_time_minutes": plan.max_time_minutes,
        "snap_to_network": plan.snap_to_network,
        "runs": [r.to_dict() for r in plan.runs],
        "core_wall_limit_hours": plan.core_wall_limit_hours,
        "origins_count": plan.origins.count,
        "destinations_count": plan.destinations.count,
        "rehearsal_origins": list(plan.rehearsal_origins),
    }


def _with_counts(plan: MatrixPlan, params: Mapping[str, Any]) -> MatrixPlan:
    """The plan with the table sizes and the rehearsal origins the parameters name (the
    samples override the sizes; a crafted table may name no rehearsal origin at all)."""
    return replace(
        plan,
        origins=replace(plan.origins, count=int(params["origins_count"])),
        destinations=replace(plan.destinations, count=int(params["destinations_count"])),
        rehearsal_origins=tuple(str(g) for g in params["rehearsal_origins"]),
    )


def find_night(
    data_root: Path,
    plan: MatrixPlan,
    *,
    points_sha256: str,
    input_digests: Mapping[str, Mapping[str, Any]],
) -> tuple[str | None, str | None]:
    """The latest night of this plan (same file digest) on the same points whose completed
    core runs recorded the same input digests: ``("reuse", id)`` when finished,
    ``("resume", id)`` when stopped, ``(None, None)`` otherwise."""
    for directory in reversed(list_nights(data_root)):
        night = Night.load(directory)
        if night.data["plan"]["name"] != plan.name or night.data["plan"]["sha256"] != plan.sha256:
            continue
        if night.data["points"]["sha256"] != points_sha256 or night.data["origins"]["subset"]:
            continue
        same_inputs = True
        for run in plan.core_runs:
            entry = night.runs[run]
            if entry["status"] != COMPLETED:
                continue
            record_path = directory / entry["dir"] / records.RECORD_FILE
            recorded = (
                records.read_json(record_path).get("inputs", {}) if record_path.is_file() else {}
            )
            if {k: v.get("sha256") for k, v in recorded.items()} != {
                k: v.get("sha256") for k, v in input_digests.items()
            }:
                same_inputs = False
        if not same_inputs:
            continue
        if night.state == FINISHED:
            return "reuse", night.id
        if night.state == STOPPED:
            return "resume", night.id
    return None, None


def combine_matrices(night: Night, plan: MatrixPlan) -> pd.DataFrame:
    """The core runs' matrices as one table in the dictionary's shape, sorted by key."""
    frames = [
        pd.read_parquet(night.dir / night.runs[run]["dir"] / MATRIX_FILE) for run in plan.core_runs
    ]
    matrix = pd.concat(frames, ignore_index=True)
    if list(matrix.columns) != list(MATRIX_COLUMNS):
        raise StageError(
            f"a run's matrix does not carry the dictionary's columns: {list(matrix.columns)}"
        )
    if matrix.duplicated(list(MATRIX_KEY)).any():
        raise StageError("the core runs' matrices repeat a key")
    expected = (
        night.data["origins"]["count"] * night.data["destinations"]["count"] * len(plan.core_runs)
    )
    if len(matrix) != expected:
        raise StageError(f"the matrix has {len(matrix)} rows, expected {expected}")
    return matrix.sort_values(list(MATRIX_KEY), kind="stable").reset_index(drop=True)


def make_travel_times(
    *,
    toolchain: Toolchain | None = None,
    runner: Callable[..., RunRecord] = harness.run,
    inputs: Mapping[str, str] | None = None,
    check: Callable[[Toolchain], ToolchainReport] = toolchain_check,
) -> Callable[[StageContext], None]:
    """The stage body bound to a toolchain (default: the project-local one), a runner
    (default: the harness; the tests pass a scripted child), and the toolchain check
    (the tests pass one that accepts their crafted record)."""

    def travel_times(ctx: StageContext) -> None:
        """Route the plan's core runs as a night (or re-use / resume one) and write the
        matrix and its report."""
        from phillysim.routing.smoke import network_inputs  # noqa: PLC0415 - avoid a cycle

        plan = load_plan(ctx.params["plan"])
        if plan.sha256 != ctx.params["plan_sha256"]:
            raise StageError(
                f"plan {plan.source} has digest {plan.sha256[:12]}, the stage expects "
                f"{str(ctx.params['plan_sha256'])[:12]}: the packaged plan changed under "
                "the registration"
            )
        plan = _with_counts(plan, ctx.params)
        chain = toolchain or Toolchain.default()
        report = check(chain)
        if not report.ok:
            raise StageError(
                "the routing toolchain is not usable here; the travel_times stage needs "
                "`uv sync --locked --group routing` and `phillysim toolchain install` first: "
                + "; ".join(line.strip() for line in report.lines())
            )
        for rel in (NETWORK_DIR, NETWORK_REPORT):
            ctx.input(rel)  # declared, so the driver may read them under the root
        network = dict(inputs) if inputs is not None else network_inputs(ctx.root)
        ctx.checkpoint()
        points = build_points(ctx.root, plan)
        scratch = ctx.staging / "points-probe.parquet"
        scratch.parent.mkdir(parents=True, exist_ok=True)
        write_points(points, scratch)
        points_sha256 = records.sha256_file(scratch)
        scratch.unlink()
        digests = records.input_digests(ctx.root, network)
        action, night_id_ = find_night(
            ctx.root, plan, points_sha256=points_sha256, input_digests=digests
        )
        if action == "reuse":
            log.info(
                "travel_times: re-using finished night %s (same plan, points, inputs)", night_id_
            )
            night = Night.load(ctx.root / records.RUNS_DIR / night_id_)
        else:
            if action == "resume":
                log.info("travel_times: resuming stopped night %s", night_id_)
            else:
                log.info("travel_times: routing the plan's core runs as a new night")
            night = run_matrix(
                plan,
                data_root=ctx.root,
                toolchain=chain,
                night_id_=night_id_,
                runner=runner,
                inputs=network,
                echo=lambda line: log.info("travel_times: %s", line),
            )
        ctx.checkpoint()
        if night.state != FINISHED:
            raise StageError(
                f"routing night {night.id} ended {night.state}"
                + (f" ({night.data.get('kill_reason') or night.data.get('stop_reason')})")
                + "; the next `phillysim run` resumes a stopped night; a killed night is evidence "
                "for the owner, not a retry"
            )
        matrix = combine_matrices(night, plan)
        digests_out = write_matrix(matrix, ctx.output(TRAVEL_TIMES))
        summary = {
            "stage": STAGE_NAME,
            "license_bucket": LICENSE_BUCKET,
            "license_note": (
                "computed over the clipped OpenStreetMap network (ODbL, Bucket B by derivation, "
                "ADR-0003) and SEPTA's GTFS schedules (facts, no feed contents); not published "
                "before M5"
            ),
            "plan": {
                "file": plan.source,
                "sha256": plan.sha256,
                "runs": [r.to_dict() for r in plan.runs],
            },
            "night_id": night.id,
            "night_reused": action == "reuse",
            "night_resumed": action == "resume",
            "points_sha256": points_sha256,
            "inputs": {k: dict(v) for k, v in digests.items()},
            "core_wall_seconds": night.data.get("core_wall_seconds"),
            "peak_rss_bytes": night.data.get("peak_rss_bytes"),
            "runs": {
                run: {
                    "wall_seconds": night.runs[run].get("wall_seconds"),
                    "peak_rss_bytes": night.runs[run].get("peak_rss_bytes"),
                    "matrix": night.runs[run].get("matrix"),
                    "sanity": night.runs[run].get("sanity"),
                }
                for run in plan.core_runs
            },
            "matrix": {
                **digests_out,
                "path": TRAVEL_TIMES,
                "modes": sorted(matrix["mode"].unique()),
            },
        }
        records.write_json(
            ctx.output(TRAVEL_TIMES_REPORT), summary, harness.scrub_roots(ctx.root, chain)
        )

    return travel_times


__all__ = [
    "LICENSE_BUCKET",
    "PLAN",
    "POINTS_FILE",
    "STAGE_NAME",
    "TRAVEL_TIMES",
    "TRAVEL_TIMES_REPORT",
    "combine_matrices",
    "find_night",
    "make_travel_times",
    "stage_params",
    "stage_plan",
]
