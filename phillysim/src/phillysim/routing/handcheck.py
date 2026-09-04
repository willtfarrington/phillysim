"""The hand check (EP-15; ADR-0008): ten origin–destination pairs by rule, forty
project-side times, and the tally against a public trip planner's answers.

**The pairs, by rule** (EP-15 brief; owner decision at EP-11, question 3): every
fortieth tract in sorted GEOID order from the first (ten of the 408), each
paired with its nearest supermarket-format retailer by the QA slice's rule
(planar distance in the analysis CRS); the fifth and tenth paired instead
with the **farthest** supermarket-format retailer inside the censor, read
here as the retailer with the largest typical walk time under 120 minutes in
the night's core walk run, so that the long tail is covered for both modes
(a walk that long has a real transit alternative). A tract the planner can
give no answer for is **substituted by the next tract in sorted order** under
the same rule (``skip``); the substitution is recorded, never a fabricated
check.

**The times.** Each pair is routed in EP-13's single-departure mode (a
one-minute window) at 08:30 and at 17:30 on the pinned Wednesday, for walk
and for walk+transit: two harness runs (one per departure, both modes) under
``<night>/handcheck/``, forty checks. The project-side minutes are the
typical time R5 reports (integer minutes; a pair with no route within the
censor is recorded as censored).

**The planner side is a person in a browser.** Nothing here reaches any
planner: ``planner.csv`` is typed by hand (``check_id,planner_minutes``, a
blank where the planner gave no answer), the tally is computed from it
(tolerance: walk within 3 minutes or 15 % of the planner's minutes,
whichever is larger; walk+transit within 10 minutes or 25 %; the gate is 32
of 40), and only the tally and the per-check differences are recorded in the
packet's handoff. The typed file stays under the gitignored data root.
"""

from __future__ import annotations

import csv
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from phillysim.destinations import SNAP_RETAILERS
from phillysim.routing import harness, records
from phillysim.routing.matrix import MATRIX_FILE, Night
from phillysim.routing.plan import MatrixPlan, load_plan
from phillysim.routing.records import MODES, Point, RunPlan, RunRecord
from phillysim.spine import ANALYSIS_CRS, SPINE, centroids_in

HANDCHECK_DIR = "handcheck"
HANDCHECK_FILE = "handcheck.json"
PLANNER_FILE = "planner.csv"
HANDCHECK_SCHEMA_VERSION = 1
#: The rule's numbers (EP-15 brief, ADR-0008).
EVERY = 40
PAIRS = 10
LONG_TAIL_POSITIONS: tuple[int, ...] = (5, 10)
DEPARTURE_TIMES: tuple[str, ...] = ("08:30", "17:30")
#: Tolerance per mode: (minutes, share of the planner's minutes), whichever is larger.
TOLERANCE: Mapping[str, tuple[float, float]] = {"walk": (3.0, 0.15), "walk_transit": (10.0, 0.25)}
GATE = (32, 40)
RULE_NEAREST = (
    "nearest supermarket-format retailer by planar distance in the analysis CRS (the QA "
    "slice's rule)"
)
RULE_FARTHEST = (
    "farthest supermarket-format retailer inside the censor: the largest typical walk time "
    "under 120 min in the night's core walk run (the long tail)"
)


def _slug(departure_time: str) -> str:
    return f"handcheck-{departure_time.replace(':', '')}"


# --- the pairs --------------------------------------------------------------------------------


def pick_origins(
    geoids: Iterable[str], *, every: int = EVERY, count: int = PAIRS, skip: Iterable[str] = ()
) -> list[dict[str, Any]]:
    """Every ``every``-th GEOID in sorted order from the first, ``count`` of them; a skipped
    GEOID is replaced by the next one in sorted order that is not itself picked or skipped."""
    ordered = sorted(set(geoids))
    skipped = set(skip)
    picks: list[dict[str, Any]] = []
    taken: set[str] = set()
    for position, index in enumerate(range(0, len(ordered), every), 1):
        if position > count:
            break
        chosen, candidate = ordered[index], index
        substituted_for = None
        while chosen in skipped or chosen in taken:
            substituted_for = substituted_for or chosen
            candidate += 1
            if candidate >= len(ordered):
                raise ValueError(f"no substitute tract after {ordered[index]} in sorted order")
            chosen = ordered[candidate]
        taken.add(chosen)
        picks.append(
            {
                "position": position,
                "geoid": chosen,
                "rule_index": index,
                "substituted_for": substituted_for,
            }
        )
    return picks


def select_pairs(
    spine: gpd.GeoDataFrame,
    retailers: gpd.GeoDataFrame,
    walk_matrix: pd.DataFrame,
    *,
    max_time: int,
    every: int = EVERY,
    count: int = PAIRS,
    long_tail: Sequence[int] = LONG_TAIL_POSITIONS,
    skip: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """The ten pairs: origin (the tract's spine center), destination (a supermarket-format
    retailer by the position's rule), both as WGS 84 coordinates, with the straight-line
    metres and the core walk run's typical time for the pair."""
    supermarkets = retailers[retailers["supermarket_format"].astype(bool)].to_crs(ANALYSIS_CRS)
    if supermarkets.empty:
        raise ValueError("no supermarket-format retailer in the layer")
    centers = centroids_in(spine, ANALYSIS_CRS)
    walk = walk_matrix[walk_matrix["mode"] == "walk"].set_index(["origin_geoid", "site_id"])
    pairs: list[dict[str, Any]] = []
    for pick in pick_origins(spine["geoid"].astype(str), every=every, count=count, skip=skip):
        geoid = pick["geoid"]
        row = spine[spine["geoid"].astype(str) == geoid]
        center = centers.loc[row.index[0]]
        distances = supermarkets.geometry.distance(center)
        if pick["position"] in long_tail:
            times = walk.loc[geoid] if geoid in walk.index.get_level_values(0) else None
            if times is None:
                raise ValueError(f"the walk matrix has no rows for origin {geoid}")
            candidates = times.loc[times.index.intersection(supermarkets["site_id"].astype(str))]
            finite = candidates[candidates["time_median_min"] < max_time]
            if finite.empty:
                raise ValueError(f"origin {geoid} reaches no supermarket-format retailer on foot")
            best = finite["time_median_min"].max()
            site_id = sorted(finite[finite["time_median_min"] == best].index)[0]
            rule = RULE_FARTHEST
        else:
            site_id = str(supermarkets.loc[distances.idxmin(), "site_id"])
            rule = RULE_NEAREST
        site = supermarkets[supermarkets["site_id"].astype(str) == site_id].iloc[0]
        walk_time = (
            walk.loc[(geoid, site_id), "time_median_min"]
            if (geoid, site_id) in walk.index
            else None
        )
        pairs.append(
            {
                **pick,
                "origin_geoid": geoid,
                "origin_name": str(row["name"].iloc[0]) if "name" in row.columns else "",
                "origin_lon": float(row["centroid_lon"].iloc[0]),
                "origin_lat": float(row["centroid_lat"].iloc[0]),
                "site_id": site_id,
                "site_name": str(site["name"]) if "name" in site.index else "",
                "site_lon": float(site["longitude"]),
                "site_lat": float(site["latitude"]),
                "straight_line_m": round(float(distances.loc[site.name]), 1),
                "core_walk_typical_min": None if walk_time is None else float(walk_time),
                "rule": rule,
            }
        )
    return pairs


# --- the runs ---------------------------------------------------------------------------------


def handcheck_plans(
    pairs: Sequence[Mapping[str, Any]],
    plan: MatrixPlan,
    inputs: Mapping[str, str],
    *,
    departure_times: Sequence[str] = DEPARTURE_TIMES,
) -> list[RunPlan]:
    """One harness plan per departure time, both modes, a one-minute window (EP-13's
    single-departure mode), the night's percentiles, censor, and snap setting; the ten
    origins and the distinct destinations."""
    core = plan.run(plan.core_runs[0])
    origins = tuple(Point(p["origin_geoid"], p["origin_lon"], p["origin_lat"]) for p in pairs)
    seen: dict[str, Point] = {}
    for p in pairs:
        seen.setdefault(p["site_id"], Point(p["site_id"], p["site_lon"], p["site_lat"]))
    speed = core.speed_walking_kmh
    return [
        RunPlan(
            slug=_slug(when),
            modes=MODES,
            speed_walking_kmh=speed,
            departure=f"{plan.dates['wednesday']}T{when}",
            time_zone=plan.time_zone,
            window_minutes=1,
            percentiles=plan.percentiles,
            max_time_minutes=plan.max_time_minutes,
            origins=origins,
            destinations=tuple(seen.values()),
            inputs=dict(inputs),
            origins_description=(
                "the hand check's ten tract centers (every fortieth tract by GEOID)"
            ),
            destinations_description="the ten pairs' supermarket-format retailers",
            note=f"EP-15 hand check: single departure {when} on the pinned Wednesday, both modes",
            snap_to_network=plan.snap_to_network,
        )
        for when in departure_times
    ]


def checks_from_records(
    pairs: Sequence[Mapping[str, Any]],
    runs: Mapping[str, tuple[RunRecord, pd.DataFrame]],
    *,
    max_time: int,
) -> list[dict[str, Any]]:
    """The forty checks: per pair, departure, and mode the project-side typical minutes."""
    out: list[dict[str, Any]] = []
    for when, (record, output) in runs.items():
        table = output.set_index(["mode", "from_id", "to_id"])
        for pair in pairs:
            for mode in MODES:
                key = (mode, pair["origin_geoid"], pair["site_id"])
                minutes = None
                if key in table.index:
                    value = table.loc[key, "travel_time_p50"]
                    minutes = None if pd.isna(value) else float(value)
                censored = minutes is None or minutes >= max_time
                out.append(
                    {
                        "check_id": f"{pair['position']:02d}-{when.replace(':', '')}-{mode}",
                        "position": pair["position"],
                        "departure_time": when,
                        "mode": mode,
                        "origin_geoid": pair["origin_geoid"],
                        "site_id": pair["site_id"],
                        "project_minutes": None if censored else minutes,
                        "censored": censored,
                        "run_id": record.run_id,
                    }
                )
    return out


def run_handcheck(
    night_dir: Path,
    *,
    data_root: Path,
    toolchain: Any,
    runner: Callable[..., RunRecord] = harness.run,
    inputs: Mapping[str, str] | None = None,
    skip: Iterable[str] = (),
    every: int = EVERY,
    count: int = PAIRS,
    plan: MatrixPlan | None = None,
    echo: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Select the pairs from the night's tables and core walk run, route them at both
    departures, and write ``handcheck.json`` (the tally empty until the planner file).
    ``plan`` defaults to the night's packaged plan file."""
    from phillysim.routing.smoke import network_inputs  # noqa: PLC0415 - avoid a cycle

    say = echo or (lambda _line: None)
    night_dir, data_root = night_dir.resolve(), data_root.resolve()
    night = Night.load(night_dir)
    plan = plan or load_plan(night.data["plan"]["file"])
    walk_run = next(r for r in plan.core_runs if plan.run(r).mode == "walk")
    walk_matrix = pd.read_parquet(night_dir / night.runs[walk_run]["dir"] / MATRIX_FILE)
    spine = gpd.read_parquet(data_root / SPINE)
    retailers = gpd.read_parquet(data_root / SNAP_RETAILERS)
    pairs = select_pairs(
        spine,
        retailers,
        walk_matrix,
        max_time=plan.max_time_minutes,
        every=every,
        count=count,
        skip=skip,
    )
    for pair in pairs:
        say(
            f"pair {pair['position']:2d}: {pair['origin_geoid']} -> {pair['site_id']} "
            f"({pair['site_name']}; {pair['straight_line_m']:.0f} m; core walk "
            f"{pair['core_walk_typical_min']} min)"
            + (f"; substituted for {pair['substituted_for']}" if pair["substituted_for"] else "")
        )
    inputs = dict(inputs) if inputs is not None else network_inputs(data_root)
    directory = night_dir / HANDCHECK_DIR
    directory.mkdir(exist_ok=True)
    runs: dict[str, tuple[RunRecord, pd.DataFrame]] = {}
    for run_plan_ in handcheck_plans(pairs, plan, inputs):
        when = run_plan_.departure[-5:]
        run_dir = directory / run_plan_.slug
        if run_dir.exists():
            aside = run_dir.with_name(f"{run_dir.name}.{records.utc_stamp()}")
            run_dir.rename(aside)
            say(f"{run_plan_.slug}: earlier run kept as {aside.name}")
        record = runner(
            run_plan_,
            data_root=data_root,
            toolchain=toolchain,
            run_id=f"{night.id}/{HANDCHECK_DIR}/{run_plan_.slug}",
            run_dir=run_dir,
            echo=say,
        )
        if record.outcome != records.COMPLETED:
            raise RuntimeError(f"{run_plan_.slug}: {record.outcome}: {record.error}")
        runs[when] = (record, records.read_output(run_dir / records.OUTPUT_FILE))
    checks = checks_from_records(pairs, runs, max_time=plan.max_time_minutes)
    report = {
        "schema_version": HANDCHECK_SCHEMA_VERSION,
        "night_id": night.id,
        "date": plan.dates["wednesday"],
        "time_zone": plan.time_zone,
        "departure_times": list(DEPARTURE_TIMES),
        "speed_walking_kmh": plan.run(plan.core_runs[0]).speed_walking_kmh,
        "max_time_minutes": plan.max_time_minutes,
        "rule": {
            "every": every,
            "count": count,
            "long_tail_positions": list(LONG_TAIL_POSITIONS),
            "nearest": RULE_NEAREST,
            "farthest": RULE_FARTHEST,
            "skipped": sorted(set(skip)),
        },
        "tolerance": {mode: {"minutes": m, "share": s} for mode, (m, s) in TOLERANCE.items()},
        "gate": list(GATE),
        "pairs": pairs,
        "runs": {when: r.run_id for when, (r, _) in runs.items()},
        "checks": checks,
        "planner_file": PLANNER_FILE,
        "tally": {"checks": len(checks), "within": None},
    }
    records.write_json(
        directory / HANDCHECK_FILE, report, harness.scrub_roots(data_root, toolchain)
    )
    return report


# --- the tally ------------------------------------------------------------------------------


def tolerance_minutes(mode: str, planner_minutes: float) -> float:
    minutes, share = TOLERANCE[mode]
    return max(minutes, share * planner_minutes)


def read_planner_file(path: Path) -> dict[str, float | None]:
    """``check_id,planner_minutes`` typed by hand; a blank or non-numeric value is no answer."""
    out: dict[str, float | None] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            check_id = (row.get("check_id") or "").strip()
            if not check_id:
                continue
            raw = (row.get("planner_minutes") or "").strip()
            try:
                out[check_id] = float(raw) if raw else None
            except ValueError:
                out[check_id] = None
    return out


def tally(report: Mapping[str, Any], planner: Mapping[str, float | None]) -> dict[str, Any]:
    """Each check against the planner's minutes: the difference, the tolerance, within or
    not; a check with no planner answer, or a censored project time, is not within."""
    max_time = int(report["max_time_minutes"])
    rows: list[dict[str, Any]] = []
    within = 0
    for check in report["checks"]:
        answer = planner.get(check["check_id"])
        project = check["project_minutes"]
        row = {
            "check_id": check["check_id"],
            "mode": check["mode"],
            "project_minutes": project,
            "planner_minutes": answer,
            "difference_minutes": None,
            "tolerance_minutes": None,
            "within": False,
            "note": "",
        }
        if answer is None:
            row["note"] = "no planner answer"
        elif project is None:
            row["note"] = f"project time censored at {max_time} min"
            if answer >= max_time:
                row["within"], row["note"] = True, f"both at or over {max_time} min"
        else:
            row["difference_minutes"] = round(project - answer, 1)
            row["tolerance_minutes"] = round(tolerance_minutes(check["mode"], answer), 1)
            row["within"] = abs(project - answer) <= row["tolerance_minutes"]
        within += int(row["within"])
        rows.append(row)
    gate, of = report.get("gate", GATE)
    by_mode = {
        mode: {
            "checks": sum(1 for r in rows if r["mode"] == mode),
            "within": sum(1 for r in rows if r["mode"] == mode and r["within"]),
        }
        for mode in MODES
    }
    return {
        "checks": len(rows),
        "within": within,
        "gate": [gate, of],
        "gate_met": bool(len(rows) >= of and within >= gate),
        "no_answer": sum(1 for r in rows if r["planner_minutes"] is None),
        "by_mode": by_mode,
        "rows": rows,
    }


def apply_planner(night_dir: Path, planner_path: Path | None = None) -> dict[str, Any]:
    """Read the hand-typed planner file, compute the tally, and write it into
    ``handcheck.json``. Returns the updated report."""
    directory = night_dir / HANDCHECK_DIR
    path = directory / HANDCHECK_FILE
    report = records.read_json(path)
    planner = read_planner_file(planner_path or directory / PLANNER_FILE)
    report["tally"] = tally(report, planner)
    records.write_json(path, report, {})
    return report


def planner_template(report: Mapping[str, Any]) -> str:
    """The CSV the owner fills in: one row per check, the planner column blank."""
    lines = ["check_id,planner_minutes"]
    lines.extend(f"{c['check_id']}," for c in report["checks"])
    return "\n".join(lines) + "\n"


# --- printing ---------------------------------------------------------------------------------


def _when(report: Mapping[str, Any], when: str) -> str:
    day = datetime.strptime(report["date"], "%Y-%m-%d").strftime("%a %Y-%m-%d")
    return f"{day} {when} ({report['time_zone']})"


def _minutes(value: float | None, absent: str) -> str:
    return absent if value is None else f"{value:.0f}"


def handcheck_lines(report: Mapping[str, Any]) -> list[str]:
    out = [
        f"hand check for night {report['night_id']}: {len(report['pairs'])} pairs, "
        f"{len(report['checks'])} checks; walk {report['speed_walking_kmh']} km/h; departures "
        + ", ".join(_when(report, w) for w in report["departure_times"])
    ]
    out.append("pairs (origin = the tract's population-weighted center; WGS 84 lat, lon):")
    for p in report["pairs"]:
        out.append(
            f"  {p['position']:2d}. {p['origin_geoid']} "
            f"({p['origin_lat']:.6f}, {p['origin_lon']:.6f})"
            f" -> {p['site_id']} {p['site_name']} ({p['site_lat']:.6f}, {p['site_lon']:.6f});"
            f" {p['straight_line_m']:.0f} m straight line; "
            + ("farthest" if p["rule"] == RULE_FARTHEST else "nearest")
            + (f"; substituted for {p['substituted_for']}" if p.get("substituted_for") else "")
        )
    out.append("checks (project-side typical minutes; '>=120' = censored):")
    for c in report["checks"]:
        minutes = ">=120" if c["censored"] else f"{c['project_minutes']:.0f}"
        out.append(f"  {c['check_id']:<22} {minutes:>6}")
    tally_ = report.get("tally") or {}
    if tally_.get("within") is None:
        out.append(
            f"tally: pending; type the planner's minutes into {report['planner_file']} under the "
            "handcheck directory (check_id,planner_minutes) and run `route handcheck --planner`"
        )
    else:
        out.append(
            f"tally: {tally_['within']} of {tally_['checks']} within tolerance "
            f"({'meets' if tally_['gate_met'] else 'BELOW'} the {tally_['gate'][0]} of "
            f"{tally_['gate'][1]} gate); no answer for {tally_['no_answer']}; by mode "
            + ", ".join(f"{m} {v['within']}/{v['checks']}" for m, v in tally_["by_mode"].items())
        )
        for r in tally_["rows"]:
            diff = "-" if r["difference_minutes"] is None else f"{r['difference_minutes']:+.0f}"
            tol = "-" if r["tolerance_minutes"] is None else f"{r['tolerance_minutes']:.0f}"
            out.append(
                f"  {r['check_id']:<22} project {_minutes(r['project_minutes'], '>=120'):>6}"
                f"  planner {_minutes(r['planner_minutes'], '-'):>5}"
                f"  diff {diff:>5}  tol {tol:>3}  {'within' if r['within'] else 'OUT'}"
                + (f"  ({r['note']})" if r["note"] else "")
            )
    return out


def with_counts(plan: MatrixPlan, origins: int, destinations: int) -> MatrixPlan:
    """A copy of the plan expecting other table sizes (the tests' crafted tables)."""
    return replace(
        plan,
        origins=replace(plan.origins, count=origins),
        destinations=replace(plan.destinations, count=destinations),
    )


__all__ = [
    "GATE",
    "HANDCHECK_DIR",
    "HANDCHECK_FILE",
    "PLANNER_FILE",
    "TOLERANCE",
    "apply_planner",
    "checks_from_records",
    "handcheck_lines",
    "handcheck_plans",
    "pick_origins",
    "planner_template",
    "read_planner_file",
    "run_handcheck",
    "select_pairs",
    "tally",
    "tolerance_minutes",
    "with_counts",
]
